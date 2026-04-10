FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.runtime.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.runtime.txt

COPY . .

EXPOSE 5000

CMD ["python", "run.py"]
