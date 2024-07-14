FROM python:3.11-slim

WORKDIR /app

COPY tracker tracker

COPY main.py main.py

RUN pip install bcoding zmq

ENTRYPOINT ["python", "main.py"]