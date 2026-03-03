FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install werkzeug==2.3.7

COPY . .

CMD ["python", "app.py"]