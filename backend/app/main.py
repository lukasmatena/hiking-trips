from fastapi import FastAPI
import asyncio
import asyncpg
from os import environ

app = FastAPI()

pg_user = environ.get("POSTGRES_USER")
pg_pass = environ.get("POSTGRES_PASSWORD")
pg_host = environ.get("POSTGRES_HOST")
pg_port = environ.get("POSTGRES_PORT")
pg_db   = environ.get("POSTGRES_DB")

@app.get("/")
async def hello_world():
    return "Hello from Python backend!"

@app.get("/test_db/")
async def test_db():
    db_url: str = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    try:
        conn = await asyncpg.connect(dsn=db_url, timeout=5)
    except asyncpg.exceptions.InvalidPasswordError:
        print(f"Connection failed: Invalid password for user '{pg_user}'")
        return "NOK - Invalid password"
    except asyncpg.exceptions.CannotConnectNowError as e:
        print(f"Connection failed: Cannot connect now (e.g., server down, wrong host/port). Error: {e}")
        return "NOK - Cannot connect to server"
    except ConnectionRefusedError as e:
        print(f"Connection failed: Connection refused by server. Error: {e}")
        return "NOK - Connection refused"
    except TimeoutError:
        print(f"Connection failed: Connection attempt timed out.")
        return "NOK - Connection timeout"
    except Exception as e:
        print(f"Connection failed: An unexpected error occurred: {type(e).__name__} - {e}")
        return f"NOK - An unexpected error occurred: {type(e).__name__}"
    #finally:
    #    if conn:
    #        await conn.close()

    try:
        #await conn.execute("DROP TABLE IF EXISTS trips")
        #await conn.execute("CREATE TABLE trips ( id NUMERIC PRIMARY KEY, title VARCHAR(255) );")
        #await conn.execute("INSERT INTO trips VALUES (2, 'druhy');")
        return await conn.fetch("SELECT * FROM trips;")
    except Exception as e:
        return f"NOK - An unexpected error occurred: {type(e).__name__}"
    if conn:
        await conn.close()

    return "OK"
