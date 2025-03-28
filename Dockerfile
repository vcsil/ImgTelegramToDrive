FROM python:3.12-slim-bookworm

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    ffmpeg \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set TimeZone
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Cria diretórios internos e ajusta permissões
RUN mkdir -p /app/midias_baixadas /app/plataformas /app/logs \
    && chmod -R a+rwx /app/midias_baixadas /app/plataformas /app/logs

# Copia os scripts
COPY . .