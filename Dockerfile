ARG PYTHON_VERSION=3.11.7
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p static/uploads templates \
    && chown -R appuser:appuser /app \
    && chmod -R 755 static templates

COPY . .
COPY templates/index.html templates/
RUN chown -R appuser:appuser /app/templates/index.html

USER appuser

EXPOSE 8080

CMD ["./run.sh"]

