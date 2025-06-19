FROM python:3.10-slim

# set working directory
WORKDIR /app

# copy files
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY webhook_receiver.py .

# run using gunicorn on port 8080
CMD ["gunicorn", "-b", ":8080", "webhook_receiver:app"]