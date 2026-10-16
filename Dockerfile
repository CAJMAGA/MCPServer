FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# server.py shells out to the OpenSSH client to reach Windows endpoints.
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-client \
 && rm -rf /var/lib/apt/lists/*

# Run as a non-root user. Set UID/GID to match the owner of the SSH files
# mounted from the host, because ssh refuses keys owned by another user.
ARG UID=1000
ARG GID=1000
RUN groupadd --gid "${GID}" mcp \
 && useradd --uid "${UID}" --gid "${GID}" --create-home mcp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the files needed at runtime. .env is never copied into the image;
# settings are supplied by docker-compose.yml.
COPY server.py config.py audit.py ./
COPY tools/ tools/

# Audit log directory; server.py refuses to start if it is not writable.
RUN mkdir -p /app/logs && chown mcp:mcp /app/logs

USER mcp

EXPOSE 8000

CMD ["python", "server.py"]
