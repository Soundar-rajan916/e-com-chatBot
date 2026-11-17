FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic

COPY server.py /app/server.py

EXPOSE 2785

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "2785"]
