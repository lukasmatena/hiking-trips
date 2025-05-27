FROM debian:stable

RUN apt update && apt upgrade && apt -y install python3 pip python3-venv
COPY ./requirements.txt /home/requirements.txt


WORKDIR /home
RUN python3 -m venv venv && venv/bin/pip install -r requirements.txt

WORKDIR /home/app
