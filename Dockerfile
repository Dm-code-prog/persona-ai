# Use a minimal Python base image
FROM python:3.10-slim

# System packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create a working directory
WORKDIR /app

# Copy all source code
COPY . /app

# Install Python libraries
# Feel free to pin versions in a requirements.txt if you prefer.
RUN pip install --no-cache-dir \
    python-dotenv \
    openai \
    elevenlabs \
    requests \
    google-api-python-client \
    youtube_transcript_api \
    fastapi \
    uvicorn[standard] \
    pydantic

# Expose the FastAPI port (change if you want something other than 8080)
EXPOSE 8080

# By default, run the FastAPI server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8080"]