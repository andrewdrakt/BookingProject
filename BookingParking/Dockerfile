FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN apt-get update \
  && apt-get install -y --no-install-recommends netcat-openbsd \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["bash", "/app/entrypoint.sh"]

