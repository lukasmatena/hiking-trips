import logging
import sys

from fastapi import FastAPI, Depends, HTTPException

from app_init import app_init
from s3_handling import get_s3_client
from database import db_get_connection, db_get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

app = FastAPI(lifespan=app_init)



@app.get("/")
async def hello_world():
    return "Hello from Python backend!"

@app.get("/read_db/")
async def read_db(conn = Depends(db_get_connection)):    
    try:
        async with conn.transaction(readonly = True):
            trips = await conn.fetch("SELECT * FROM trips;")
            photos = await conn.fetch("SELECT * FROM photos;")
            return {"trips_table": list(trips), "photos_table": list(photos)}
    except Exception as e:
        raise HTTPException(status_code=503, detail = f"Error occurred: {type(e).__name__}")

@app.get("/reset_db/")
async def reset_db(conn = Depends(db_get_connection)):
    try:
        async with conn.transaction(readonly = False):
            await conn.execute("""
                DROP TABLE IF EXISTS photos;
                DROP TABLE IF EXISTS trips;
                CREATE TABLE trips (
                    trip_id SERIAL PRIMARY KEY,
                    title VARCHAR(255),
                    description TEXT);
                CREATE TABLE photos (
                    photo_id SERIAL PRIMARY KEY,
                    trip_id INT,
                    CONSTRAINT fk_trips_photos
                        FOREIGN KEY (trip_id)
                        REFERENCES trips(trip_id)
                        ON DELETE RESTRICT
                );
                """)
            await conn.execute("""
                INSERT INTO trips (title, description) VALUES ('titulek1', 'text1');
                INSERT INTO trips (title, description) VALUES ('titulek2', 'text2');
                INSERT INTO trips (title, description) VALUES ('titulek3', 'text3');
            """)
            await conn.execute("""
                INSERT INTO photos (trip_id) VALUES (1);
            """)
    except Exception as e:
        logging.error(f"Failed to reset database: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail = f"{type(e).__name__}")
    return "OK"



@app.get("/trips/{trip_id}")
async def get_trip(trip_id: int, conn = Depends(db_get_connection)):
    try:
        async with conn.transaction(readonly = True):
            query = f"SELECT * FROM trips WHERE trip_id=$1"
            trip_data = await conn.fetchrow(query, trip_id)
            query = "SELECT photos.photo_id FROM photos WHERE trip_id=$1;"
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


@app.get("/s3_list_buckets/")
async def list_buckets(s3_client = Depends(get_s3_client)):
    return s3_client.list_buckets()
