FROM python:3.12-slim

COPY requirements-docs.txt /tmp/requirements-docs.txt
RUN pip install --no-cache-dir -r /tmp/requirements-docs.txt

WORKDIR /work
EXPOSE 8000
