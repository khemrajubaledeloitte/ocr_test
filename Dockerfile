# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all your project files into container
COPY . /app

# Install tesseract-ocr and dependencies
RUN apt-get update && apt-get install -y tesseract-ocr libtesseract-dev

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (make sure your app listens on this port)
EXPOSE 8000

# Start your FastAPI app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
