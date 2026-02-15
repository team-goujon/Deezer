FROM python:3.14-slim

WORKDIR /app

COPY service ./service
COPY utils ./utils
COPY webapp.py .
COPY templates ./templates
COPY requirements.txt .
COPY config.ini .

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "webapp.py"]