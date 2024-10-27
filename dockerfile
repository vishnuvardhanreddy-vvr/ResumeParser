FROM python:3.11

WORKDIR /

# Install antiword, LibreOffice, and any additional dependencies
RUN apt-get update && \
    apt-get install -y antiword libreoffice tesseract-ocr && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /requirements.txt

RUN pip install -r /requirements.txt

# RUN playwright install chromium
# RUN playwright install-deps chromium

COPY ./app /app/
# WORKDIR /app

CMD ["fastapi", "run", "/app/main.py", "--port", "5000"]

# If running behind a proxy like Nginx or Traefik add --proxy-headers
# CMD ["fastapi", "run", "app/main.py", "--port", "80", "--proxy-headers"]