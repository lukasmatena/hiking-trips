FROM python:3.11-slim-bullseye

COPY ./requirements.txt /home/requirements.txt

WORKDIR /home
RUN python3 -m venv venv && venv/bin/pip install --no-cache-dir -r requirements.txt

COPY ./app/* /home/app/
WORKDIR /home/app
