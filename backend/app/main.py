from fastapi import FastAPI, Depends, HTTPException
from database import db_connection_pool_init, db_get_connection


app = FastAPI(lifespan=db_connection_pool_init)


@app.get("/")
async def hello_world():
    return "Hello from Python backend!"

@app.get("/test_db/")
async def test_db(conn = Depends(db_get_connection)):    
    try:
        async with conn.transaction(readonly = True):
            return await conn.fetch("SELECT * FROM trips;")
    except Exception as e:
        raise HTTPException(status_code=503, detail = f"Error occurred: {type(e).__name__}")

@app.get("/reset_db/")
async def reset_db(conn = Depends(db_get_connection)):
    try:
        async with conn.transaction(readonly = False):
            await conn.execute("""
                               DROP TABLE IF EXISTS trips;
                               CREATE TABLE trips (id SERIAL PRIMARY KEY, title VARCHAR(255), description TEXT);
                               INSERT INTO trips (title, description) VALUES ('titulek1', 'text1');
                               INSERT INTO trips (title, description) VALUES ('titulek2', 'text2');
                               INSERT INTO trips (title, description) VALUES ('titulek3', 'text3');
                               """)
    except Exception as e:
        raise HTTPException(status_code=503)
