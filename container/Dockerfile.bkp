FROM python:3.9

ARG VERSION=0.0.0
ARG POETRY_VERSION=1.1.6

LABEL "Version" = $VERSION
LABEL "Name" = "ml-flow-server"


# Add user admin
RUN useradd -m -s /bin/bash admin && \
    usermod -aG sudo admin && \
    passwd -d admin1 
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

# Install poetry and ml-flow-server
RUN pip install "poetry==$POETRY_VERSION" --user \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi \
    mlflow \
    pymysql \
    boto3 & \
    mkdir /mlflow/

EXPOSE 5000

## Environment variables made available through the task.
## Do not enter values
CMD mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --default-artifact-root ${BUCKET} \
    --backend-store-uri mysql+pymysql://${USERNAME}:${PASSWORD}@${HOST}:${PORT}/${DATABASE}
