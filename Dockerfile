FROM python:3.12-slim

# Устанавливаем зависимости для компиляции
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
