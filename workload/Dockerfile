FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/srv
WORKDIR /srv
COPY requirements-workload.lock /srv/
RUN pip install --no-cache-dir --require-hashes -r requirements-workload.lock \
    && groupadd --gid 10001 kavach && useradd --uid 10001 --gid 10001 --no-create-home kavach
COPY workload /srv/workload
USER 10001:10001
CMD ["python", "/srv/workload/entrypoint.py"]
