FROM python:3.11

RUN useradd -m -U app

# dirs
RUN mkdir /app
WORKDIR /app
RUN chown -R app /app

# entrypoint magic
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER app

# Mount the entire build context (including '.git/') just for this step
# NOTE:
#  - mounting '.git/' allows the Python project to build with 'setuptools-scm'
#  - no 'COPY .' because we don't want to copy extra files (especially '.git/')
#  - using '/tmp/pip-cache' allows pip to cache
RUN --mount=type=cache,target=/tmp/pip-cache \
    pip install --upgrade "pip>=25" "setuptools>=80" "wheel>=0.45"
RUN pip install virtualenv
RUN python -m virtualenv /app/venv
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN --mount=type=bind,source=.,target=/src,ro \
    --mount=type=cache,target=/tmp/pip-cache \
    bash -euxo pipefail -c '\
      . /app/venv/bin/activate && \
      pip install --upgrade pip && \
      mkdir -p /tmp/pkg && cp -a /src/. /tmp/pkg/ && \
      pip install --no-cache-dir --use-pep517 /tmp/pkg \
    '


# go
ENTRYPOINT ["/entrypoint.sh"]
# note: ^^^ entrypoint activates the python virtual env
CMD ["python", "-m", "tms"]
