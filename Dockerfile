##############################
# Stage 1: Builder – Install Dependencies and Build the App
##############################
FROM python:3.10.11-slim AS builder

# Install build dependencies for native extensions (e.g. libpq for PostgreSQL)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gettext-base && \
    rm -rf /var/lib/apt/lists/*

# Set working directory for the builder stage
WORKDIR /app

# Copy the requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Clean NULL bytes and non-UTF-8 characters from requirements.txt
RUN tr -d '\000' < requirements.txt | iconv -f utf-8 -t utf-8 -c > cleaned.txt && mv cleaned.txt requirements.txt

# Upgrade pip and install Python dependencies globally (no virtualenv used)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the builder
COPY . .

##############################
# Stage 2: Runner – Prepare the Production Image
##############################
FROM python:3.10.11-slim

# Set environment variables to improve runtime behavior
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory for the runtime stage
WORKDIR /app

# Install only runtime system dependencies (libpq-dev required by your app)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from the builder stage (global install from /usr/local)
COPY --from=builder /usr/local /usr/local

# Copy the application code from the builder stage
COPY --from=builder /app /app

# Create a non-root user for improved container security and adjust file ownership
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose the port on which the FastAPI app will run (optional)
# EXPOSE 8000

# Command to start the FastAPI application using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
