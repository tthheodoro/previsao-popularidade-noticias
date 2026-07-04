# Python 3.11 slim for smaller image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Expose port
EXPOSE 7860

# Run with gunicorn (app is in app/ package)
CMD ["gunicorn", "app.servidor:app", "--bind", "0.0.0.0:7860", "--timeout", "120", "--workers", "2"]
