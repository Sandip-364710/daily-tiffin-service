
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /tiffin

COPY requirements.txt /tiffin/
RUN pip install -r requirements.txt

COPY  tiffin_service /tiffin


CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]







