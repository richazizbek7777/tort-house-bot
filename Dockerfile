FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cashe-dir -r requirements.txt

COPY . .

CMD ["python", "bakery_bot_ideal.py"]