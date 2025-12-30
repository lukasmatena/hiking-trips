FROM python:3.11-slim-bullseye

COPY ./requirements.txt /home/requirements.txt

WORKDIR /home
RUN python3 -m venv venv && venv/bin/pip install --no-cache-dir -r requirements.txt

COPY ./app/ /home/app/
COPY ./alembic/ /home/alembic/
COPY ./alembic.ini /home/alembic.ini

WORKDIR /home/app

# Default CMD to run. PORT env var is passed from GCP Cloud Run.
CMD exec ../venv/bin/uvicorn main:app_inst --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers

