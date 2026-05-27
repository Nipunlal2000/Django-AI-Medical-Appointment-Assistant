FROM python:3.12.3-slim

ENV PYTHONUNBUFFERED 1

RUN mkdir /testApp

WORKDIR /testApp

COPY . /testApp/

RUN pip install -r requirements.txt

