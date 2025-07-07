# 🔨 Stage 1: Builder
FROM python:3.12-bullseye AS builder

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONOTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --prefix=/install -r requirements.txt

COPY . .



# 🚀 Stage 2: Final Runtime Image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONOTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /install /usr/local

COPY --from=builder /app /app

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
