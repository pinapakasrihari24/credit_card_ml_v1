FROM python:3.12-slim

WORKDIR /app

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and data (from credit_card_ml subdirectory)
COPY credit_card_ml/src/ ./src/
COPY credit_card_ml/data/sample/ ./data/sample/
COPY credit_card_ml/data/raw/ ./data/raw/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Run the application
CMD ["python", "-m", "src.visualization.app"]
