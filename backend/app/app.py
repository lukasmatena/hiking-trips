from fastapi import FastAPI, Request, HTTPException
from os import environ
import google.cloud
import asyncpg
import logging
from contextlib import asynccontextmanager

def db_get_pool(request: Request):
    if not hasattr(request.app.state, "pool") or not request.app.state.pool:
        raise HTTPException(status_code=503, detail="DB pool not initialized.")
    return request.app.state.pool

async def db_get_connection(request: Request):
    async with db_get_pool(request).acquire() as conn:
        yield conn

async def get_storage_bucket(request: Request):
    if not hasattr(request.app.state, "gcp_storage_bucket") or not request.app.state.gcp_storage_bucket:
        raise HTTPException(status_code=503, detail="Unable to access GCP Storage bucket.")
    yield request.app.state.gcp_storage_bucket

@asynccontextmanager
async def app_init(app_inst: FastAPI):
    logging.info("Application initialization starts.")
    
    # Initialize db connection pool
    logging.info(" - init db connection pool...")
    pg_user = environ.get("POSTGRES_USER")
    pg_pass = environ.get("POSTGRES_PASSWORD")
    pg_host = environ.get("POSTGRES_HOST")
    pg_port = environ.get("POSTGRES_PORT")
    pg_db   = environ.get("POSTGRES_DB")
    db_url: str = ""
    if pg_host.startswith("/"):
        # Cloud Run (Unix Socket) - Host goes in query params, NO PORT in authority
        db_url = f"postgresql://{pg_user}:{pg_pass}@/{pg_db}?host={pg_host}"
    else:
        # Local/TCP - Standard Host:Port format
        db_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    try:
        pool = await asyncpg.create_pool(dsn = db_url, timeout = 5)
    except Exception as e:
        logging.error(f"Unable to connect to the db.")
        raise e
    logging.info(" - db connection pool created.")

    # Initialize GCP Storage handle
    gcp_storage_client = google.cloud.storage.Client()
    logging.info(" - GCP Storage client created")
    
    bucket_name: str | None = environ.get("GCP_STORAGE_BUCKET_NAME")
    if not bucket_name:
        raise Exception("ERROR: unknown GCP Storage bucket name")

    bucket = gcp_storage_client.bucket(bucket_name) # no network call yet
    try:
        # This is for local devlopment, where we need to ensure the bucket exists.
        bucket.create(location="europe-west1")
        logging.info(f" - Created new bucket: {bucket_name}")
    except google.cloud.exceptions.Conflict:
        logging.info(f" - Bucket {bucket_name} already exists (Local)")
    except google.cloud.exceptions.Forbidden:
        # Production: We are not allowed to create buckets.
        # We assume Terraform already created it and proceed.
        logging.info(f" - explicit creation denied for {bucket_name}, assuming infrastructure exists (Production)")
    except Exception as e:
        logging.error(f" - Unexpected error connecting to bucket {bucket_name}")
        raise e
    if not bucket:
        raise Exception(f"ERROR: GCP Storage bucket not available ({bucket_name})")

    # Save both to app state
    app_inst.state.pool = pool
    app_inst.state.gcp_storage_bucket = bucket

    logging.info("Application initialization finished.")
    yield

    # Cleanup
    logging.info("Cleaning up on application close...")
    await pool.close()
    logging.info("Cleanup complete.")

app_inst = FastAPI(lifespan=app_init, openapi_prefix="/api")