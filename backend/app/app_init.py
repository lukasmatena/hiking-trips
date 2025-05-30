from fastapi import FastAPI
from os import environ
import asyncpg
import boto3
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

    # Initialize S3 handle
    logging.info(" - init S3 connection...")
    s3_url  = environ.get("S3_ENDPOINT_URL")
    s3_user = environ.get("S3_USERNAME")
    s3_pass = environ.get("S3_PASSWORD")
    s3_client = boto3.client('s3', endpoint_url=s3_url, region_name="eu-central-1", aws_access_key_id = s3_user, aws_secret_access_key = s3_pass)
    logging.info(" - S3 client created")

    # Save both to app state
    app.state.pool = pool
    app.state.s3_client = s3_client

    logging.info("Application initialization finished.")
    yield

    # Cleanup
    logging.info("Cleaning up on application close...")
    await pool.close()
    s3_client.close()
    logging.info("Cleanup complete.")