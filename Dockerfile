# Use Python 3.11 slim image with security updates
FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages:/usr/local/lib/python3.11/site-packages/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY app/requirements.txt .

# Install Python dependencies - сначала устанавливаем aiohttp из бинарных пакетов
RUN pip install wheel && \
    pip install --only-binary :all: aiohttp==3.8.5 && \
    pip install --no-cache-dir aiogram==2.25.1 && \
    pip install --no-cache-dir -r requirements.txt && \
    python -c "import sys; print(f'Python version: {sys.version}')" && \
    python -c "import aiohttp; print(f'aiohttp version: {aiohttp.__version__}')" && \
    echo "DOCKER_CONTAINER=true" >> /etc/environment

# Copy application code
COPY app/ .
COPY start.py ../start.py
COPY cloud_run_adapter.py ../cloud_run_adapter.py
COPY debug_imports.py ../debug_imports.py
COPY debug_cloud_run.py ../debug_cloud_run.py
COPY fix_imports.py ../fix_imports.py

# Create directory for modules in Python path and make sure reminder_system.py is in all possible locations
RUN mkdir -p /usr/local/lib/python3.11/site-packages/app
COPY app/reminder_system.py /usr/local/lib/python3.11/site-packages/app/
COPY app/reminder_system.py /usr/local/lib/python3.11/site-packages/
COPY app/reminder_system.py /app/

# Create symlinks to make imports more robust
RUN ln -sf /app/reminder_system.py /usr/local/lib/python3.11/site-packages/reminder_system.py && \
    ln -sf /app/reminder_system.py /usr/local/lib/python3.11/site-packages/app/reminder_system.py

# Fix imports in bot.py
RUN cd .. && python fix_imports.py

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port 8080 for Cloud Run health checks
EXPOSE 8080

# Command to run the application using start.py
CMD ["python", "../start.py"]
