FROM python:3.8

ARG VERSION=0.0.0

LABEL "Version" = $VERSION
LABEL "Name" = "ml-flow-server"


# Add user admin
RUN useradd -m -s /bin/bash admin && \
    usermod -aG sudo admin && \
    passwd -d admin && \
    mkdir /mlflow && \
    chown admin:admin /mlflow && \
    echo 'admin:admin1' | chpasswd

#
# Declare environment variables
ENV YOUR_ENV=${YOUR_ENV} \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin \
    PATH=$PATH:/usr/bin:/sbin:/bin:/home/admin/.local/bin

USER admin

WORKDIR /home/admin

COPY --chown=admin pyproject.toml .
# Install poetry ml-flow-server and change admin password
RUN pip install poetry --user \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi
    
EXPOSE 5000

## Environment variables made available through the task.
## Do not enter values
CMD mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --default-artifact-root ${BUCKET} \
    --backend-store-uri mysql+pymysql://${USERNAME}:${PASSWORD}@${HOST}:${PORT}/${DATABASE}
