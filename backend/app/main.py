import logging
import sys
import uuid
import os
import asyncio
import datetime

from fastapi import Depends, HTTPException, UploadFile, concurrency, Request
import asyncpg
from pydantic import BaseModel

from app_init import app
from s3_handling import get_s3_client
from database import db_get_connection, db_get_connection, db_get_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


def get_next_prev_query() -> str:
    return """
        WITH ordered_trips AS (
            SELECT
                trip_id,
                title,
                date_start,
                LAG(trip_id, 1) OVER (ORDER BY "date_start" ASC, trip_id ASC) AS prev_trip_id,
                LEAD(trip_id, 1) OVER (ORDER BY "date_start" ASC, trip_id ASC) AS next_trip_id
            FROM
                trips
        )
        SELECT
            prev_trip_id,
            next_trip_id
        FROM
            ordered_trips
        WHERE
            trip_id = $1;
    """

async def get_photo_url_internal(photo_id: int, request: Request, s3_client) -> str:
    pool = await db_get_pool(request)
    async with pool.acquire() as conn:
        async with conn.transaction(readonly = True):
            record = await conn.fetchrow("SELECT s3_key FROM photos WHERE photo_id=$1;", photo_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="Photo not found")
    url = await concurrency.run_in_threadpool(s3_client.generate_presigned_url, ClientMethod = 'get_object',
                            Params={'Bucket': app.state.s3_bucket_name, 'Key': record["s3_key"]},
                            ExpiresIn=3600)
    return url



@app.get("/read_db")
async def read_db(conn = Depends(db_get_connection)):
    """TESTING ONLY"""
    try:
        async with conn.transaction(readonly = True):
            trips = await conn.fetch("SELECT * FROM trips;")
            photos = await conn.fetch("SELECT * FROM photos;")
            return {"trips_table": list(trips), "photos_table": list(photos)}
    except Exception as e:
        raise HTTPException(status_code=503, detail = f"Error occurred: {type(e).__name__}")

@app.put("/reset_db")
async def reset_db(conn = Depends(db_get_connection)):
    """
    This request recreates the db from scratch from the given schema,
    destroing everything what is in there. Use with caution!
    """
    try:
        async with conn.transaction(readonly = False):
            await conn.execute("""
                DROP TABLE IF EXISTS photos;
                DROP TABLE IF EXISTS trips;
                CREATE TABLE trips (
                    trip_id SERIAL PRIMARY KEY,
                    title VARCHAR(255),
                    description TEXT,
                    date_start DATE,
                    date_end DATE);
                CREATE TABLE photos (
                    photo_id SERIAL PRIMARY KEY,
                    trip_id INT,
                    s3_key TEXT,
                    CONSTRAINT fk_trips_photos
                        FOREIGN KEY (trip_id)
                        REFERENCES trips(trip_id)
                        ON DELETE RESTRICT
                );
                """)
    except Exception as e:
        logging.error(f"Failed to reset database: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail = f"{type(e).__name__}")


class TripBasicData(BaseModel):
    trip_id: int
    title: str
    date_start: datetime.date
    date_end: datetime.date


@app.get("/trips", response_model=list[TripBasicData])
async def get_trips(conn = Depends(db_get_connection)):
    try:
        async with conn.transaction(readonly = True):
            trips = await conn.fetch("SELECT trip_id,title,date_start,date_end FROM trips;")
            return [dict(trip) for trip in trips]
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unable to retrieve trips: {type(e).__name__}")



class TripDetailData(BaseModel):
    trip_id: int
    title: str
    description: str
    date_start: datetime.date
    date_end: datetime.date
    prev_trip_id: int | None
    next_trip_id: int | None
    urls: list[str]

@app.get("/trips/{trip_id}", response_model=TripDetailData)
async def get_trip(trip_id: int, request: Request, conn = Depends(db_get_connection), s3_client = Depends(get_s3_client)):
    try:
        async with conn.transaction(readonly = True):
            query = f"SELECT * FROM trips WHERE trip_id=$1"
            trip_data = await conn.fetchrow(query, trip_id)
            query = "SELECT photo_id FROM photos WHERE trip_id=$1;"
            photos_list = await conn.fetch(query, trip_id)
            if not trip_data:
                logging.error(f"Trip {trip_id} not found.")
                raise HTTPException(status_code=404, detail=f"Trip {trip_id} not found.")
            neighbors = await conn.fetchrow(get_next_prev_query(), trip_id)
        coros = [get_photo_url_internal(p["photo_id"], request, s3_client) for p in photos_list]
        urls = await asyncio.gather(*coros)
        out = {k:v for (k,v) in trip_data.items()}
        out = out | {k:v for (k,v) in neighbors.items()}
        out["urls"] = urls
        return out
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Unable to retrieve trip from db: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Error: {type(e).__name__}")



class CreateTripData(BaseModel):
    title: str
    text: str
    start_date: datetime.date
    end_date: datetime.date

@app.post("/trips/")
async def create_trip(trip_data: CreateTripData, conn = Depends(db_get_connection)):
    try:
        async with conn.transaction():
            await conn.execute("""
                INSERT INTO trips (title, description, date_start, date_end)
                VALUES ($1, $2, $3, $4);""",
                trip_data.title, trip_data.text, trip_data.start_date, trip_data.end_date)
    except Exception as e:
        raise HTTPException(status_code=503, detail="Unable to add trip into db")



@app.delete("/trips/{trip_id}")
async def delete_trip(trip_id: int, conn = Depends(db_get_connection)):
    try:
        async with conn.transaction():
            await conn.execute("DELETE FROM trips WHERE trip_id=$1", trip_id)
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise HTTPException(status_code=400, detail="Cannot delete trip as it has photos attached.")
    except Exception as e:
        raise HTTPException(status_code=503, detail="Unable to delete trip from db")



@app.delete("/photos/{photo_id}")
async def delete_photo(photo_id: int, conn = Depends(db_get_connection), s3_client = Depends(get_s3_client)):
    try:
        async with conn.transaction(readonly = False):
            record = await conn.fetchrow("SELECT s3_key FROM photos WHERE photo_id=$1;", photo_id)
            if not record:
                raise HTTPException(status_code=404, detail="Photo not found.")
            await concurrency.run_in_threadpool(s3_client.delete_object, Bucket = app.state.s3_bucket_name, Key = record["s3_key"])
            await conn.execute("DELETE FROM photos WHERE photo_id=$1", photo_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.warning(f"Problem deleting photo: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Unable to delete photo from db")



@app.post("/photos/{trip_id}")
async def upload_photo(trip_id: int, file: UploadFile, conn = Depends(db_get_connection), s3_client = Depends(get_s3_client)):
    try:
        if not file.filename:
            raise HTTPException(status_code=400)
        _, ext = os.path.splitext(file.filename)
        s3_key = str(trip_id) + "/" + str(uuid.uuid4()) + ext
        async with conn.transaction():
            await conn.execute("INSERT INTO photos (trip_id, s3_key) VALUES ($1, $2);", trip_id, s3_key)
            await concurrency.run_in_threadpool(s3_client.upload_fileobj, Fileobj = file.file, Bucket = app.state.s3_bucket_name, Key = s3_key)
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise HTTPException(status_code=404, detail="Cannot upload photo: trip does not exist.")
    except Exception as e:
        logging.warning(f"Error uploading photo: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Unable to upload photo")



@app.get("/photo/{photo_id}")
async def get_photo_url(photo_id: int, request: Request, s3_client = Depends(get_s3_client)):
    try:
        url: str = await get_photo_url_internal(photo_id, request, s3_client)
        return { "url": url}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.warning(f"Error getting photo url: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Unable to get photo url")
