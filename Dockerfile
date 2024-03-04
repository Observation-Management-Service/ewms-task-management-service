FROM python:3.12

RUN useradd -m -U app

WORKDIR /home/app
USER app

COPY --chown=app:app . .

# venv
RUN python3 -m virtualenv tms_venv
RUN . tms_venv/bin/activate
RUN pip install --upgrade pip

# install
RUN pip install --no-cache-dir .
# ENV PYTHONPATH=/home/app

# entrypoint magic
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

CMD ["python", "-m", "tms"]
