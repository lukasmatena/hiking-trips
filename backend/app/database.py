from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from os import environ
import asyncpg

@asynccontextmanager
async def db_connection_pool_init(app: FastAPI):
    pg_user = environ.get("POSTGRES_USER")
    pg_pass = environ.get("POSTGRES_PASSWORD")
    pg_host = environ.get("POSTGRES_HOST")
    pg_port = environ.get("POSTGRES_PORT")
    pg_db   = environ.get("POSTGRES_DB")
    db_url: str = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    pool = await asyncpg.create_pool(dsn = db_url, timeout = 5)
    app.state.pool = pool
    yield
    await pool.close()
    
async def db_get_connection(request: Request):
    if not hasattr(request.app.state, "pool") or not request.app.state.pool:
        raise HTTPException(status_code=503, detail="DB pool not initialized.")
    async with request.app.state.pool.acquire() as conn:
        yield conn


