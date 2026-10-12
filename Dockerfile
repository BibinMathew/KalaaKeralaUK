FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN DEBUG=true python manage.py collectstatic --noinput \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/media && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["sh", "scripts/start.sh"]
