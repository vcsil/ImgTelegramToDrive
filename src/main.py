# -*- coding: utf-8 -*-
"""
Created on Sat Feb  8 13:58:16 2025.

@author: vinic
"""
from logging.handlers import RotatingFileHandler
from pyrogram import Client, filters, idle
from organize_groups import organize_image
from pyrogram.errors import FloodWait
from dotenv import dotenv_values
import nest_asyncio
import functools
import logging
import asyncio
import os

# Aplica o patch para permitir múltiplos loops
nest_asyncio.apply()

env = dotenv_values()

# Configurações
api_id = env["TELEGRAM_API_ID"]
api_hash = env["TELEGRAM_API_HASH"]
phone_number = env["TELEGRAM_PHONE_NUMBER"]
group_username = env["TELEGRAM_GROUP_USERNAME"]
download_folder = os.path.join("..", env["FIRST_DONWLOAD_FOLDER"])

log_file = os.path.join("..", "logs", "log.txt")  # Nome do arquivo de log
max_log_size = 2 * 1024 * 1024  # Tamanho máximo do arquivo de log (2MB)
backup_count = 3  # Número de arquivos de log de backup

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            log_file, maxBytes=max_log_size, backupCount=backup_count
        ),
        logging.StreamHandler()  # Para exibir logs no console também
    ]
)
logger = logging.getLogger(__name__)


# Decorador para capturar e aguardar FloodWait
def handle_flood_wait(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        while True:
            try:
                return await func(*args, **kwargs)
            except FloodWait as e:
                except_str = f"⚠️ FLOOD_WAIT detectado! Aguardando {e.value} "
                except_str += "segundos antes de tentar novamente..."
                print(except_str)
                logger.warning(except_str)
                # Espera o tempo necessário antes de tentar novamente
                await asyncio.sleep(e.value)
    return wrapper


# Função para criar diretórios se não existirem
def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)


# Função para processar mídias
async def process_media(message):
    try:
        if message.media:
            # Obtém a data da mensagem
            message_date = message.date
            # Formata a data como "YYYY-MM-DD"
            date_folder = message_date.strftime("%Y-%m-%d")
            # Cria o diretório correspondente à data
            media_folder = os.path.join(download_folder, date_folder)
            create_directory(media_folder)

            # Define a extensão do arquivo com base no tipo de mídia
            if message.photo:
                file_extension = ".jpg"
            elif message.video:
                file_extension = ".mp4"
            elif message.document:
                file_extension = os.path.splitext(
                    message.document.file_name)[1]
            else:
                # Extensão padrão para outros tipos de mídia
                file_extension = ".dat"

            # Define o nome do arquivo
            file_name = os.path.join(media_folder,
                                     f"{message.id}{file_extension}")

            # Baixa a mídia
            logger.info(f"Baixando mídia da mensagem {message.id}...")
            await app.download_media(message, file_name=file_name)
            logger.info(
                f"Mídia {message.id} baixada com sucesso em {media_folder}!")

            # Se for uma imagem, processa e organiza
            if message.photo:
                organize_image(file_name)

    except FloodWait as e:
        # Captura o erro FloodWait e espera o tempo necessário
        wait_time = e.x
        logger.warning(
            f"FloodWait detectado. Esperando {wait_time}s antes de continuar.")
        await asyncio.sleep(wait_time)
        # Tenta processar a mídia novamente após a espera
        await process_media(message)

    except Exception as e:
        logger.error(f"Erro ao processar a mensagem {message.id}: {e}")


# Função para baixar mídias antigas
@handle_flood_wait
async def download_media_from_group(group_id):
    async with app:
        print("Conectado à conta do Telegram!")
        group = await app.get_chat(group_id)
        print(f"Acessando o grupo: {group.title}")

        id_image = 38821

        async for message in app.get_chat_history(group.id):
            try:
                if message.photo and message.id > id_image:
                    # Obtém a data da mensagem
                    message_date = message.date
                    # Formata a data como "YYYY-MM-DD"
                    date_folder = message_date.strftime("%Y-%m-%d")
                    # Cria o diretório correspondente à data
                    media_folder = os.path.join(download_folder, date_folder)
                    if not os.path.exists(media_folder):
                        os.makedirs(media_folder)

                    # Define a extensão do arquivo com base no tipo de mídia
                    if message.photo:
                        file_extension = ".jpg"
                    elif message.video:
                        file_extension = ".mp4"
                    elif message.document:
                        file_extension = os.path.splitext(message.document
                                                          .file_name)[1]
                    else:
                        # Extensão padrão para outros tipos de mídia
                        file_extension = ".dat"

                    # Define o nome do arquivo
                    file_name = os.path.join(media_folder,
                                             f"{message.id}{file_extension}")

                    logger.info(f"Baixando mídia da mensagem {message.id}...")
                    print(f"Baixando mídia da mensagem {message.id}...")
                    await app.download_media(message, file_name=file_name)

                    print_txt = f"Mídia {message.id} baixada com sucesso "
                    print_txt += f"em {media_folder}!"
                    logger.info(print_txt)
                    print(print_txt)
                elif message.id <= id_image:
                    break
                    print("Stop!")

            except Exception as e:
                logger.error(f"Erro ao processar a mensagem {message.id}: {e}")
                print(f"Erro ao processar a mensagem {message.id}: {e}")
                await asyncio.sleep(1)


# Retorna os id dos chats
async def list_groups():
    group_id = ""
    async with app:
        async for dialog in app.get_dialogs():
            print(f"Nome: {dialog.chat.title} | ID: {dialog.chat.id}")
            if dialog.chat.title == group_username:
                group_id = dialog.chat.id
                break

    return group_id

# Cria a pasta de download, se não existir
create_directory(download_folder)

create_directory(os.path.join("..", "sessions"))

# Inicializa o cliente
app = Client("minha_conta", api_id=api_id, api_hash=api_hash,
             phone_number=phone_number, workdir=os.path.join("..", "sessions"))

# Pegar id dos grupoas
group_id = int(env["TELEGRAM_GROUP_ID"])  # app.run(list_groups())  #


# Executa o script de baixar mídias antigas
# =============================================================================
# app.run(download_media_from_group(group_id))
# =============================================================================


# Handler para novas mensagens
# Filtra apenas mensagens do grupo especificado
@app.on_message(filters.chat(group_id))
async def handle_new_message(client, message):
    logger.info(f"Nova mensagem recebida: {message.id}")
    await process_media(message)


# Função principal para iniciar o cliente
async def main():
    await app.start()
    logger.info("Cliente iniciado. Aguardando novas mensagens...")

    try:
        await idle()  # Mantém o cliente em execução
    except KeyboardInterrupt:
        logger.info("Encerrando o cliente...")
    finally:
        await app.stop()


# Executa o script
if __name__ == "__main__":
    asyncio.run(main())
