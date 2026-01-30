# official and latest Python image
FROM python:3.14-slim

WORKDIR /app

# copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy application code
COPY app.py .
COPY app ./app

EXPOSE 5000

CMD ["python", "app.py"]