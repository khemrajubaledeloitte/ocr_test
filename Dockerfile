FROM python:3.11-slim

WORKDIR /app

# Copy source code
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y tesseract-ocr libtesseract-dev

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (for local use; Render ignores this)
EXPOSE 8000

# Run the app with shell so $PORT expands
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
