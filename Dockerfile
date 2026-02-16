FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/kb chroma_db

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
