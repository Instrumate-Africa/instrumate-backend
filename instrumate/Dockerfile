FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m nltk.downloader punkt_tab

COPY migrations.sh /migrations.sh
RUN chmod +x /migrations.sh
ENTRYPOINT ["/migrations.sh"]

COPY . .
EXPOSE 8000

CMD [ "gunicorn", "instrumate.asgi:application", "-k", "uvicorn_worker.UvicornWorker", "--bind", "0.0.0.0:8000" ]
