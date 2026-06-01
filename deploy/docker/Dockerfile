FROM python:3.13-slim-bookworm AS base

FROM base AS python-build-stage

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    python3-dev

COPY requirements ./requirements

RUN pip wheel --wheel-dir /usr/src/app/wheels -r requirements/production.txt

FROM base AS final

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /project/

RUN apt-get update && apt-get install --no-install-recommends -y \
    cron \
    libpq5 \
    procps \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

COPY --from=python-build-stage /usr/src/app/wheels /wheels/
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
    && rm -rf /wheels/

COPY deploy/docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY . /project/

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]