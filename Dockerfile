FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# migrate + (опционально) создание суперюзера из env vars — удобно для демо,
# чтобы не лазить в shell контейнера на проде.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py createsuperuser --noinput 2>/dev/null || true; python manage.py runserver 0.0.0.0:8000"]
