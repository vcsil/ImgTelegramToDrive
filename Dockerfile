FROM python:3.12-slim-bookworm

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# Criar diretório de trabalho
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    ffmpeg \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    build-essential \
    nano \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar apenas os arquivos de requisitos primeiro para otimizar o cache
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia os scripts
COPY . .

# Set TimeZone
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Criar diretórios necessários para o funcionamento
RUN mkdir -p /app/midias_baixadas /app/plataformas /app/logs /app/credentials

# Definir permissões adequadas para os diretórios
RUN chmod -R 777 /app/midias_baixadas /app/plataformas /app/logs /app/credentials

# Usar um script para inicializar o aplicativo
COPY Docker-entrypoint.sh /
RUN chmod +x /Docker-entrypoint.sh

# Definir o comando de entrada
ENTRYPOINT ["/Docker-entrypoint.sh"]