FROM python:3.11-slim
WORKDIR /app
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt
COPY api /app/api
COPY reference_result_icons /app/reference_result_icons
COPY reference_manifest.json /app/reference_manifest.json
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "uvicorn api.external_image_matching_engine:app --host 0.0.0.0 --port ${PORT:-8000}"]
