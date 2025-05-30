from contextlib import asynccontextmanager
from fastapi import  Request, HTTPException

async def get_s3_client(request: Request):
    if not hasattr(request.app.state, "s3_client") or not request.app.state.s3_client:
        raise HTTPException(status_code=503, detail="Unable to get s3 connection.")
    yield request.app.state.s3_client
