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

RUN pip install virtualenv
RUN python -m virtualenv /app/venv
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Mount the entire build context (including '.git/') just for this step
# NOTE:
#  - mounting '.git/' allows the Python project to build with 'setuptools-scm'
#  - no 'COPY .' because we don't want to copy extra files (especially '.git/')
#  - using '/tmp/pip-cache' allows pip to cache
#COPY pyproject.toml /app/pyproject.toml
#COPY tms /app/tms
RUN --mount=type=bind,source=.git,target=.git,ro \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,ro \
    --mount=type=bind,source=tms,target=tms,ro \
    pip install --no-clean .


# go
ENTRYPOINT ["/entrypoint.sh"]
# note: ^^^ entrypoint activates the python virtual env
CMD ["python", "-m", "tms"]
