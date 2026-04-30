FROM python:3.14.4-slim-trixie AS backend
LABEL maintainer="Girish Koliki <girish@vouch.co>"

# REF: https://github.com/astral-sh/uv/releases
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

WORKDIR /code

ARG UID=1000
ARG GID=1000

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    openssh-server \
    zsh \
    ca-certificates \
    curl \
    git \
    libpq-dev \
    gettext \
    nano \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
    && apt-get clean \
    && groupadd -g "${GID}" main \
    && useradd --create-home --no-log-init -u "${UID}" -g "${GID}" main \
    && mkdir -p /data/public/static \
    && chown main:main -R /data /code

RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && NODE_MAJOR=24 \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs

RUN mkdir -p /home/main/.antigen \
    && curl -L git.io/antigen > /home/main/.antigen/antigen.zsh

COPY /zsh-config/ /home/main/
RUN chown -R main:main /home/main/.antigen /home/main/.zshrc /home/main/remy.zsh-theme

RUN npm install -g pnpm@latest

# Copy and setup entrypoint script (as root before switching users)
COPY docker/backend/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

USER main

RUN /bin/zsh /home/main/.zshrc

COPY --chown=main:main . .

ARG DEBUG="false"
ARG ENV="production"
ENV DEBUG="${DEBUG}" \
    PYTHONUNBUFFERED="true" \
    ENV="${ENV}" \
    UV_HTTP_TIMEOUT=500 \
    USER="main"

# Create virtual environment directory and set permissions
RUN mkdir -p /code/src/.venv && chown main:main /code/src/.venv

# Set PATH to include virtual environment
ENV PATH="/code/src/.venv/bin:${PATH}"

WORKDIR /code/src

EXPOSE 8000

# Set entrypoint to handle venv setup
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Option 1: Run the application with gunicorn with uvicorn worker
CMD ["gunicorn", "-c", "python:vouch.gunicorn", "vouch.asgi:application", "-k", "vouch.uvicorn.DynamicWorker"]
# Option 2: Run the application with uvicorn
# CMD ["uvicorn", "vouch.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
# Option 3: Run the application with gunicorn
# CMD ["gunicorn", "-w", "2", "--threads", "4", "-c", "python:vouch.gunicorn", "vouch.wsgi"]