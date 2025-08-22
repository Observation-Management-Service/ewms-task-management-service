FROM python:3.11

RUN useradd -m -U app

# dirs
RUN mkdir /app
WORKDIR /app
RUN chown -R app /app
RUN chown -R app /src

# entrypoint magic
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh


# Mount the entire build context (including '.git/') just for this step
# NOTE:
#  - mounting '.git/' allows the Python project to build with 'setuptools-scm'
#  - no 'COPY .' because we don't want to copy extra files (especially '.git/')
#  - using '/tmp/pip-cache' allows pip to cache
RUN --mount=type=cache,target=/tmp/pip-cache \
    pip install --upgrade "pip>=25" "setuptools>=80" "wheel>=0.45"
RUN pip install virtualenv
RUN python -m virtualenv /app/tms_venv
ENV VIRTUAL_ENV=/app/tms_venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
USER app
RUN --mount=type=bind,source=.,target=/src,rw \
    --mount=type=cache,target=/tmp/pip-cache \
    bash -euxo pipefail -c '\
      . /app/tms_venv/bin/activate && \
      pip install --upgrade pip && \
      pip install --no-cache-dir /src \
    '


# go
ENTRYPOINT ["/entrypoint.sh"]
# note: ^^^ entrypoint activates the python virtual env
CMD ["python", "-m", "tms"]
