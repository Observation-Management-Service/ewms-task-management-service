FROM python:3.12

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

# venv
RUN pip install virtualenv
RUN python -m virtualenv tms_venv
RUN . tms_venv/bin/activate
RUN pip install --upgrade pip

# install
RUN pip install --no-cache-dir .

# go
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "tms"]
