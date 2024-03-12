FROM python:3.11

RUN useradd -m -U app

RUN mkdir /app
WORKDIR /app
RUN chown -R app /app

# entrypoint magic
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# user
USER app
COPY --chown=app:app . .

# venv and install
RUN pip install virtualenv
RUN python -m virtualenv /app/tms_venv
RUN . /app/tms_venv/bin/activate && \
    pip install --upgrade pip && \
    pip install --no-cache-dir .

# go
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "tms"]
