FROM python:3.12-slim
LABEL authors="soufi mahdi"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY Requirements.txt .

RUN pip install --no-cache-dir -r Requirements.txt

COPY . .

EXPOSE 5000

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]