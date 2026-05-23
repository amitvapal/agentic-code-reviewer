# Placeholder image. PR 6 turns this into a multi-stage build that compiles the
# frontend and serves it (plus the agent API) from FastAPI. For now it just
# installs the Python deps and runs the test suite as a smoke check.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["pytest", "-q"]
