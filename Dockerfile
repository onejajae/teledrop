FROM python:3.11.7

COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

ENV PYTHONUNBUFFERED=0

WORKDIR /app
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", ":50000"]