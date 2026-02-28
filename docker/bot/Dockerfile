FROM python:3.11-slim

WORKDIR /app

# Create logs directory so the bot can write bot.log on startup
RUN mkdir -p /app/logs

COPY run_bot.py .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "run_bot.py"]