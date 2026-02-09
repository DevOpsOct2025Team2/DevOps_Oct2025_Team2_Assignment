# official and latest Python image
FROM python:3.14-slim

WORKDIR /app

# install build dependencies required for compiling native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy application code
COPY app.py .
COPY app ./app
COPY templates ./templates
COPY static ./static

# expose flask/gunicorn port
EXPOSE 5000

# run with gunicorn (production-ready)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
