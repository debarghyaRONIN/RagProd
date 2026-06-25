FROM python:3.11-slim

WORKDIR /app

# Install build tools required for compiling C-extensions (like bcrypt and greenlet)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

EXPOSE 8080

# Run uvicorn server on all interfaces inside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
