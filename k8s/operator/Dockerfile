FROM python:3.12-slim

WORKDIR /app
COPY requirements-operator.txt .
RUN pip install --no-cache-dir -r requirements-operator.txt

COPY operator.py .

CMD kopf run /app/operator.py --verbose
