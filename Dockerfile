FROM python:3.11-slim

WORKDIR /app

COPY requirements
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "bakery_bot_ideal.py"]