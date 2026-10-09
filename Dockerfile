FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --chmod=644 requirements.in /app/requirements.in
RUN pip install --no-cache-dir -r requirements.in && useradd --uid 10001 --create-home appuser
COPY --chmod=755 . /app
RUN DJANGO_DEBUG=true python manage.py collectstatic --noinput
USER 10001
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "30", "--access-logfile", "-", "--error-logfile", "-"]
