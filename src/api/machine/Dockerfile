FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update && apt-get install -y iputils-ping
# CMD ["uvicorn", "main_machine:app", "--host", "0.0.0.0", "--port", "8020", "--reload"]