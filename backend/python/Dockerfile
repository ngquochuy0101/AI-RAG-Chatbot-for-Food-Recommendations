FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install NumPy < 2.0 first to prevent PyTorch compatibility issues
RUN pip install "numpy<2.0.0"

# Install PyTorch CPU version (saves ~1-2GB) - Upgrade to >= 2.4.0
RUN pip install torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose port
EXPOSE 8001

# Run command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
