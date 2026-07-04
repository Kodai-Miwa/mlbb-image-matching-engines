FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY api/external_image_matching_engine.py /app/external_image_matching_engine.py

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "external_image_matching_engine:app", "--host", "0.0.0.0", "--port", "8000"]
