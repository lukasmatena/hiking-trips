from fastapi import  Request, HTTPException

async def get_storage_bucket(request: Request):
    if not hasattr(request.app.state, "gcp_storage_bucket") or not request.app.state.gcp_storage_bucket:
        raise HTTPException(status_code=503, detail="Unable to access GCP Storage bucket.")
    yield request.app.state.gcp_storage_bucket
