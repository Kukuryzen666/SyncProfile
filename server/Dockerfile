FROM python:3.11-slim

WORKDIR /app

COPY server.py .

ENV PORT=8000
ENV HOST=0.0.0.0
ENV SYNC_DB_PATH=/app/data/sync_profiles.db

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "server.py"]
