FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y iputils-ping curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "generate_linkstack:app"]
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "--timeout", "120", "generate_linkstack:app"]