FROM python:3.11-slim

# Install dependencies for compilation
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=10000
CMD ["python", "bot.py"]
