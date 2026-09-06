FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements-api.lock /srv/requirements-api.lock
RUN pip install --no-cache-dir --require-hashes -r requirements-api.lock \
    && groupadd --gid 10001 kavach && useradd --uid 10001 --gid 10001 --no-create-home kavach
COPY payment-api/app /srv/app
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
