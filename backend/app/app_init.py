from fastapi import FastAPI
from os import environ
from google.cloud import storage
import google.cloud
import asyncpg
import logging
from contextlib import asynccontextmanager

@asynccontextmanager
async def app_init(app: FastAPI):
    logging.info("Application initialization starts.")
    
    # Initialize db connection pool
    logging.info(" - init db connection pool...")
    pg_user = environ.get("POSTGRES_USER")
    pg_pass = environ.get("POSTGRES_PASSWORD")
    pg_host = environ.get("POSTGRES_HOST")
    pg_port = environ.get("POSTGRES_PORT")
    pg_db   = environ.get("POSTGRES_DB")
    db_url: str = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    pool = await asyncpg.create_pool(dsn = db_url, timeout = 5)
    logging.info(" - db connection pool created.")

    # Initialize GCP Storage handle
    gcp_storage_client = storage.Client()
    logging.info(" - GCP Storage client created")
    try:
        bucket_name: str | None = environ.get("GCP_STORAGE_BUCKET_NAME")
        if not bucket_name:
            raise Exception("ERROR: unknown GCP Storage bucket name")
        gcp_storage_client.create_bucket(bucket_name, timeout=10)
        logging.info(f" - GCP Storage bucket created ({bucket_name})")
    except google.cloud.exceptions.Conflict:
        logging.info(f" - GCP Storage bucket already exists ({bucket_name})")
    except Exception as e:
        logging.info(f" - ERROR: Unable to create GCP Storage bucket ({bucket_name})")
        raise e


    # Save both to app state
    app.state.pool = pool

    TODO:
    - store the bucket, not client.
    - add docker volume for the gcp
    - make sure that errors propagate to frontend (like the one with deleting non-existent files)
    - put gcp code into a separate file




    app.state.gcp_storage_client = gcp_storage_client

    logging.info("Application initialization finished.")
    yield

    # Cleanup
    logging.info("Cleaning up on application close...")
    await pool.close()
    logging.info("Cleanup complete.")

app = FastAPI(lifespan=app_init, openapi_prefix="/api")