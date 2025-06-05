from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from os import environ
import asyncpg
from pydantic import BaseModel
from datetime import date

def db_get_pool(request: Request):
    if not hasattr(request.app.state, "pool") or not request.app.state.pool:
        raise HTTPException(status_code=503, detail="DB pool not initialized.")
    return request.app.state.pool



async def db_get_connection(request: Request):
    async with db_get_pool(request).acquire() as conn:
        yield conn


class CreateTripData(BaseModel):
    title: str
    text: str
    start_date: date
    end_date: date
