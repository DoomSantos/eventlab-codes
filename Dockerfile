FROM python:3.12-slim

WORKDIR /app
COPY collector/ collector/
COPY server/ server/
COPY data/tracks.json data/tracks.json
COPY data/cars.json data/cars.json

ENV TIMING_HOST=0.0.0.0
ENV TIMING_DB=/data/timing.db
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /data

EXPOSE 8787
CMD ["python", "-m", "server"]
