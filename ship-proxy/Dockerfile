FROM python:3.11-slim

WORKDIR /app

COPY client.py .

ENV OFFSHORE_HOST=offshore-proxy
ENV OFFSHORE_PORT=9999

EXPOSE 8080
CMD ["python", "-u", "client.py"]
