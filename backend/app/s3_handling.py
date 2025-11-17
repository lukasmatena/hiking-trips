from contextlib import asynccontextmanager
from fastapi import  Request, HTTPException

from google.cloud import storage
import os

async def get_storage_bucket(request: Request):
    if not hasattr(request.app.state, "gcp_storage_client") or not request.app.state.gcp_storage_client:
        raise HTTPException(status_code=503, detail="Unable to get s3 connection.")
    
    yield request.app.state.gcp_storage_client.bucket(os.environ.get("GCP_STORAGE_BUCKET_NAME"))
