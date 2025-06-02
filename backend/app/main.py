import logging
import sys
import uuid
import os

from fastapi import FastAPI, Depends, HTTPException, UploadFile, concurrency
import asyncpg

from app_init import app_init
from s3_handling import get_s3_client
from database import db_get_connection, db_get_connection, CreateTripData

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

app = FastAPI(lifespan=app_init)


@app.get("/read_db/")
async def read_db(conn = Depends(db_get_connection)):    
    try:
        async with conn.transaction(readonly = True):
            trips = await conn.fetch("SELECT * FROM trips;")
            photos = await conn.fetch("SELECT * FROM photos;")
            return {"trips_table": list(trips), "photos_table": list(photos)}
    except Exception as e:
        raise HTTPException(status_code=503, detail = f"Error occurred: {type(e).__name__}")

@app.put("/reset_db/")
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



@app.get("/trips/{trip_id}")
async def get_trip(trip_id: int, conn = Depends(db_get_connection)):
    try:
        async with conn.transaction(readonly = True):
            query = f"SELECT * FROM trips WHERE trip_id=$1"
            trip_data = await conn.fetchrow(query, trip_id)
            query = "SELECT * FROM photos WHERE trip_id=$1;"
            photos_list = await conn.fetch(query, trip_id)
            if not trip_data:
                logging.error(f"Trip {trip_id} not found.")
                raise HTTPException(status_code=404, detail=f"Trip {trip_id} not found.")
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Unable to retrieve trip from db: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Error: {type(e).__name__}")
    out = dict(trip_data)
    out["photos_table"] = photos_list
    return out

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
async def get_photo_url(photo_id: int, conn = Depends(db_get_connection), s3_client = Depends(get_s3_client)):
    try:
        async with conn.transaction(readonly = True):
            record = await conn.fetchrow("SELECT s3_key FROM photos WHERE photo_id=$1;", photo_id)
            if not record:
                raise HTTPException(status_code=404, detail="Photo not found")
            url = await concurrency.run_in_threadpool(s3_client.generate_presigned_url, ClientMethod = 'get_object',
                                    Params={'Bucket': app.state.s3_bucket_name, 'Key': record["s3_key"]},
                                    ExpiresIn=3600)
            return url
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.warning(f"Error getting photo url: {type(e).__name__}")
        raise HTTPException(status_code=503, detail="Unable to get photo url")
