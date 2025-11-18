import logging
import sys
import uuid
import os
import asyncio
import datetime
import urllib

from fastapi import Depends, HTTPException, UploadFile, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ValidationError

import asyncpg
from google.cloud import storage

from app import app_inst
import app
from auth import create_token_or_none, reader_only, admin_only

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

async def get_photo_url_internal(photo_id: int, s3_key: str, gcp_bucket: storage.Bucket) -> tuple[int, str]:
    if os.environ.get("STORAGE_EMULATOR_HOST"):
        # This is local development. Do not bother with signed URLs.
        encoded_key = urllib.parse.quote(s3_key, safe='')
        url = f"http://localhost:4443/download/storage/v1/b/{gcp_bucket.name}/o/{encoded_key}?alt=media"
    else:
        url = await asyncio.to_thread(gcp_bucket.get_blob(s3_key).generate_signed_url,
                                  expiration=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=120))
    return (photo_id, url)



@app_inst.get("/read_db")
async def read_db(conn = Depends(app.db_get_connection), _ = Depends(admin_only)):
    """TESTING ONLY"""
    try:
        async with conn.transaction(readonly = True):
            trips = await conn.fetch("SELECT * FROM trips;")
            photos = await conn.fetch("SELECT * FROM photos;")
            return {"trips_table": list(trips), "photos_table": list(photos)}
    except Exception as e:
        raise HTTPException(status_code=503, detail = f"Error occurred: {type(e).__name__}")

@app_inst.put("/reset_db")
async def reset_db(conn = Depends(app.db_get_connection)):
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


@app_inst.get("/trips", response_model=list[TripBasicData])
async def get_trips(conn = Depends(app.db_get_connection)):
    try:
        async with conn.transaction(readonly = True):
            trips = await conn.fetch("SELECT trip_id,title,date_start,date_end FROM trips ORDER BY date_start DESC;")
            return [dict(trip) for trip in trips]
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unable to retrieve trips: {type(e).__name__}")


class PhotoData(BaseModel):
    url: str
    photo_id: int
class TripDetailData(TripBasicData, BaseModel):
    description: str
    prev_trip_id: int | None
    next_trip_id: int | None
    photos: list[PhotoData]

@app_inst.get("/trips/{trip_id}", response_model=TripDetailData)
async def get_trip(trip_id: int, request: Request, conn = Depends(app.db_get_connection), gcp_bucket = Depends(app.get_storage_bucket)):
    try:
        async with conn.transaction(readonly = True):
            query = "SELECT * FROM trips WHERE trip_id=$1"
            trip_data = await conn.fetchrow(query, trip_id)
            query = "SELECT photo_id, s3_key FROM photos WHERE trip_id=$1;"
            photos_list = await conn.fetch(query, trip_id)
            if not trip_data:
                logging.error(f"Trip {trip_id} not found.")
                raise HTTPException(status_code=404, detail=f"Trip {trip_id} not found.")
            neighbors = await conn.fetchrow(get_next_prev_query(), trip_id)
        coros = [get_photo_url_internal(p["photo_id"], p["s3_key"], gcp_bucket) for p in photos_list]
        photos = await asyncio.gather(*coros)
        out = {k:v for (k,v) in trip_data.items()}
        out = out | {k:v for (k,v) in neighbors.items()}
        out["photos"] = [ { "photo_id": photo_id, "url": url } for (photo_id, url) in photos ]
        return out
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Unable to retrieve trip from db: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Error: {type(e).__name__}")



class TripUpdateData(TripBasicData, BaseModel):
    desc: str
    photos_to_delete: list[int]

@app_inst.put("/trips/{trip_id}")
async def update_trip(
    trip_id: int,
    updated_trip_json: str = Form(...), # Changed to Form parameter
    files: list[UploadFile] = [],
    conn = Depends(app.db_get_connection),
    gcp_bucket = Depends(app.get_storage_bucket)
):
    try:
        updated_trip = TripUpdateData.model_validate_json(updated_trip_json) # Parse JSON string
        if (updated_trip.trip_id != trip_id):
            logging.error("Update trip_id mismatch")
            raise HTTPException(status_code=400, detail="Update trip_id mismatch")

        async with conn.transaction():
            await conn.execute("""
                UPDATE trips
                SET title=$1,
                    description=$2,
                    date_start=$3,
                    date_end=$4
                WHERE trip_id = $5;
            """, updated_trip.title, updated_trip.desc, updated_trip.date_start, updated_trip.date_end, trip_id)

        for photo_id in updated_trip.photos_to_delete:
            async with conn.transaction():
                record = await conn.fetchrow("SELECT s3_key FROM photos WHERE photo_id=$1;", photo_id)
                if not record:
                    raise HTTPException(status_code=404, detail="Photo not found.")
                await conn.execute("DELETE FROM photos WHERE photo_id=$1", photo_id)
                await asyncio.to_thread(gcp_bucket.delete_blob, record["s3_key"])

        for file in files:
            if not file.filename:
                raise HTTPException(status_code=400)
            _, ext = os.path.splitext(file.filename)
            s3_key = str(trip_id) + "/" + str(uuid.uuid4()) + ext
            async with conn.transaction():
                await conn.execute("INSERT INTO photos (trip_id, s3_key) VALUES ($1, $2);", trip_id, s3_key)
                bucket: storage.Bucket = gcp_bucket
                blob = bucket.blob(s3_key)
                await asyncio.to_thread(blob.upload_from_file, file.file, rewind=True)

    except ValidationError as e:
        logging.error(f"Validation error updating trip {trip_id}: {e.errors()}", exc_info=True)
        raise HTTPException(status_code=422, detail=e.errors())
    except HTTPException as e:
        logging.error(f"HTTPException when updating trip {trip_id}: {e}", exc_info=True)
        raise e
    except Exception as e:
        logging.error(f"Unable to update trip {trip_id}: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Unable to update trip {type(e).__name__}")

@app_inst.post("/trips/")
async def create_new_trip(conn = Depends(app.db_get_connection)):
    init_date = datetime.date.today()
    try:
        async with conn.transaction():
            await conn.execute("""
                INSERT INTO trips (title, description, date_start, date_end)
                VALUES ('NEW TRIP', 'desc', $1, $1);""",
                init_date)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unable to add trip into db: {type(e).__name__}")



@app_inst.delete("/trips/{trip_id}")
async def delete_trip(trip_id: int, conn = Depends(app.db_get_connection)):
    try:
        async with conn.transaction():
            await conn.execute("DELETE FROM trips WHERE trip_id=$1", trip_id)
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise HTTPException(status_code=400, detail="Cannot delete trip as it has photos attached.")
    except Exception as e:
        raise HTTPException(status_code=503, detail="Unable to delete trip from db")



@app_inst.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    token: str | None = create_token_or_none(form_data.password)
    if not token:
        raise HTTPException(status_code=401, detail="Unknown password")
    return {"access_token": token, "token_type": "bearer"}
