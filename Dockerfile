# Single-stage image: the dashboard is plain static HTML, so no Node build step
# is needed. The web demo uses the lean app dependency set (no torch/chromadb)
# and runs reviews without RAG context — see requirements-app.txt.
FROM python:3.11-slim

WORKDIR /app

COPY requirements-app.txt ./
RUN pip install --no-cache-dir -r requirements-app.txt

COPY agent/ ./agent/
COPY app/ ./app/
COPY eval/results.sample.json ./eval/results.sample.json
COPY frontend/ ./static/

ENV STATIC_DIR=/app/static
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
