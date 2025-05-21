#!/bin/bash
set -e

# Verificar se os diretórios necessários existem e têm permissões adequadas
mkdir -p /app/credentials
mkdir -p /app/logs
mkdir -p /app/midias_baixadas
mkdir -p /app/plataformas

# Garantir permissões adequadas
chmod -R 777 /app/credentials /app/logs /app/midias_baixadas /app/plataformas

# Função para registrar mensagens de log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Verificar se o arquivo .env existe
if [ ! -f /app/.env ]; then
    log "ERRO: Arquivo .env não encontrado. Crie o arquivo .env com as configurações necessárias."
    exit 1
fi

# Verificar se as credenciais do Google Drive estão presentes
if [ ! -f /app/credentials/service_account.json ]; then
    log "AVISO: service_account.json não encontrado. Certifique-se de colocá-lo na pasta credentials."
fi

# Loop infinito para reiniciar o script em caso de falha
while true; do
    log "Iniciando o aplicativo..."
    
    # Executar o script principal
    cd /app/src && python mainTelegram.py
    
    # Se o script falhar, aguardar um pouco antes de reiniciar
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        log "O script falhou com código de saída $EXIT_CODE. Reiniciando em 10 segundos..."
        sleep 10
    else
        log "O script terminou com sucesso. Reiniciando em 5 segundos..."
        sleep 5
    fi
done