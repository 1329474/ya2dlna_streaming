FROM python:3.11.9-bookworm

WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/src

EXPOSE 8001 8080

RUN mkdir -p /app/logs /app/cache

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"] 