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

EXPOSE 5000

CMD ["python", "app.py"]