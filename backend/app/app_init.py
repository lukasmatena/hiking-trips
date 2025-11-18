from fastapi import FastAPI
from os import environ
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
    try:
        pool = await asyncpg.create_pool(dsn = db_url, timeout = 5)
    except Exception as e:
        logging.error(f"Unable to connect to the db: {db_url}")
        raise e
    logging.info(" - db connection pool created.")

    # Initialize GCP Storage handle
    gcp_storage_client = google.cloud.storage.Client()
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
        logging.error(f" - Unable to create GCP Storage bucket ({bucket_name})")
        raise e

    # Save both to app state
    app.state.pool = pool

    bucket = gcp_storage_client.get_bucket(bucket_name)
    if not bucket:
        raise Exception(f"ERROR: GCP Storage bucket not available ({bucket_name})")
    app.state.gcp_storage_bucket = bucket

    logging.info("Application initialization finished.")
    yield

    # Cleanup
    logging.info("Cleaning up on application close...")
    await pool.close()
    logging.info("Cleanup complete.")

app = FastAPI(lifespan=app_init, openapi_prefix="/api")