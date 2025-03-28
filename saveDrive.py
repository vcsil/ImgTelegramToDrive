# -*- coding: utf-8 -*-
"""
Created on Sat Feb  8 19:48:55 2025.

@author: vinic
"""
from watchdog.events import FileSystemEventHandler
from logging.handlers import RotatingFileHandler
from watchdog.observers import Observer
from pydrive2.drive import GoogleDrive
from pydrive2.auth import GoogleAuth
from dotenv import dotenv_values
from tqdm import tqdm
import datetime
import logging
import time
import json
import os

env = dotenv_values()

# Configuração do logging
log_file = os.path.join("logs", "log-drive.txt")  # Nome do arquivo de log
max_log_size = 2 * 1024 * 1024  # Tamanho máximo do arquivo de log (2MB)
backup_count = 3  # Número de arquivos de log de backup

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


class OnlyErrorFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == logging.DEBUG  # Só permite ERROR


# Adiciona o filtro ao handler padrão
for handler in logging.root.handlers:
    handler.addFilter(OnlyErrorFilter())

log = logging.getLogger('root')


class GoogleDriveManager:
    def __init__(self, credentials_file="credentials.txt"):
        # Configuração do Google Drive
        self.gauth = GoogleAuth()

        # access_type 'offline' para garantir que um refresh_token seja gerado
        self.gauth.settings["access_type"] = "offline"

        # Carrega as credenciais do arquivo
        try:
            self.gauth.LoadCredentialsFile(credentials_file)
        except Exception as e:
            log.error(f"Erro ao carregar credenciais: {e}")
            raise

        if self.gauth.credentials is None:
            log.info("Realiza autenticação via linha de comando")
            self.gauth.CommandLineAuth()
        elif self.gauth.access_token_expired:
            log.info("Se o token expirou, renova")
            self.gauth.CommandLineAuth()
            # self.gauth.Refresh()
        else:
            log.info("Autenticação válida")
            self.gauth.Authorize()

        # Salva as credenciais para uso futuro
        self.gauth.SaveCredentialsFile(credentials_file)
        self.drive = GoogleDrive(self.gauth)

    def list_files(self, folder_id="root"):
        return self.drive.ListFile(
            {'q': f"'{folder_id}' in parents and trashed=false"}).GetList()

    def upload_file(self, file_path, parent_folder_id):
        """Faz o upload de um arquivo para o Google Drive."""
        file_name = os.path.basename(file_path)
        gfile = self.drive.CreateFile({'title': file_name,
                                       'parents': [{'id': parent_folder_id}]})
        gfile.SetContentFile(file_path)
        gfile.Upload()
        log.info(f'Arquivo {file_name} enviado para o Google Drive.')


drive = GoogleDriveManager().drive


def save_uploaded_dict():
    with open(uploaded_files_dirs_path, 'w') as f:
        json.dump(uploaded_files_dirs, f)


def save_uploaded_files(file_name):
    """Salva o dicionário de arquivos enviados no arquivo local."""
    uploaded_files_dirs[file_name] = True  # Marca o arquivo como enviado
    save_uploaded_dict()


def save_uploaded_dirs(parent_id, folder_name, folder_id):
    """Salva o dicionário de arquivos enviados no arquivo local."""
    if folder_id not in uploaded_files_dirs["uploaded_dirs"]:
        uploaded_files_dirs["uploaded_dirs"][folder_id] = {}

    uploaded_files_dirs["uploaded_dirs"][parent_id][folder_name] = folder_id
    save_uploaded_dict()
    return


def create_folder_in_drive(folder_name, parent_folder_id):
    """Cria uma pasta no Google Drive dentro da pasta especificada."""
    folder_metadata = {
        'title': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [{'id': parent_folder_id}]
    }
    log.info(f"Cria o diretório {folder_name} no Drive")
    folder = drive.CreateFile(folder_metadata)
    folder.Upload()
    save_uploaded_dirs(parent_folder_id, folder['title'], folder["id"])
    return folder['id']


def get_or_create_folder(folder_name, parent_folder_id):
    """Verifica se a pasta já existe no Google Drive. Se não existir, cria."""
    log.info(f"Verifica se a pasta {folder_name} já existe no Google Drive")

    if parent_folder_id not in uploaded_files_dirs["uploaded_dirs"]:
        uploaded_files_dirs["uploaded_dirs"][parent_folder_id] = {}

    if folder_name in uploaded_files_dirs["uploaded_dirs"][parent_folder_id]:
        return uploaded_files_dirs["uploaded_dirs"][parent_folder_id][folder_name]

    query = f"'{parent_folder_id}' in parents and title='{folder_name}' "
    query += "and mimeType='application/vnd.google-apps.folder' "
    query += "and trashed=false"
    folder_list = drive.ListFile({'q': query}).GetList()
    if folder_list:
        # Adiciona ao dicionário para consultas futuras
        save_uploaded_dirs(parent_folder_id, folder_list[0]['title'],
                           folder_list[0]["id"])
        return folder_list[0]['id']  # Retorna o ID da pasta existente
    else:
        # Cria uma nova pasta
        return create_folder_in_drive(folder_name, parent_folder_id)


def file_already_uploaded(file_name, parent_folder_id):
    """
    Verifica se um arquivo já foi enviado para a pasta especificada
    no Google Drive.
    """
    # Verifica primeiro no dicionário local
    if file_name in uploaded_files_dirs:
        return True

    query = f"'{parent_folder_id}' in parents and title='{file_name}' "
    query += "and trashed=false"
    file_list = drive.ListFile({'q': query}).GetList()

    if file_list:
        # Adiciona ao dicionário para consultas futuras
        save_uploaded_files(file_name)  # Salva o dicionário atualizado
        return True
    return False


def upload_file(file_path, parent_folder_id):
    """Faz o upload de um arquivo para a pasta especificada no Google Drive."""
    file_name = os.path.basename(file_path)

    if not file_already_uploaded(file_name, parent_folder_id):
        start_time = datetime.datetime.now()
        gfile = drive.CreateFile({'title': file_name,
                                  'parents': [{'id': parent_folder_id}]})
        gfile.SetContentFile(file_path)
        gfile.Upload()
        end_time = datetime.datetime.now()

        save_uploaded_files(file_name)  # Salva o dicionário atualizado

        # Converte bytes para MB
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        log_txt = f"Arquivo {file_name} ({file_size:.2f} MB) enviado em "
        log_txt += f"{(end_time - start_time).total_seconds():.2f} segundos."
        log.info(log_txt)
        return True
    else:
        log.info(f'Arquivo {file_name} já existe no Google Drive. Ignorando.')
        return False


def sync_directory(local_path, drive_parent_folder_id):
    """
    Sincroniza um diretório local com o Google Drive, mantendo a estrutura
    de pastas.
    """
    # Lista todos os arquivos para exibir uma barra de progresso geral
    all_files = []
    for root, _, files in os.walk(local_path):
        all_files.extend([os.path.join(root, file) for file in files])

    files_not_uploaded = [file_path for file_path in all_files
                          if os.path.basename(file_path)
                          not in uploaded_files_dirs]

    dirs_files_not_uploaded = {os.path.split(file_path)[0]: True
                               for file_path in files_not_uploaded}

    # Barra de progresso para o upload geral
    with tqdm(total=len(files_not_uploaded),
              desc="Sincronizando arquivos", unit="arquivo") as pbar:

        # Nevega só nas pastas que receberam fotos novas
        for path in dirs_files_not_uploaded:
            for root, dirs, files in os.walk(path):
                # Obtém o caminho relativo para criar a mesma estrutura
                # no Google Drive
                relative_path = os.path.relpath(root, local_path)
                current_folder_id = drive_parent_folder_id

                # Se não for o diretório raiz, cria as pastas correspondentes
                # no Google Drive
                if relative_path != '.':
                    for folder_name in relative_path.split(os.sep):
                        current_folder_id = get_or_create_folder(
                            folder_name, current_folder_id)

                # Faz o upload dos arquivos para a pasta atual no Google Drive
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    atualizou = upload_file(file_path, current_folder_id)
                    if atualizou:
                        pbar.update(1)  # Atualiza a barra de progresso


class SyncHandler(FileSystemEventHandler):
    def on_created(self, event):
        self.process_event(event, "criado")

    def on_moved(self, event):
        self.process_event(event, "movido")

    def on_modified(self, event):
        self.process_event(event, "modificado")

    def process_event(self, event, action_type):
        if event.is_directory:
            return

        log.info(f"Arquivo {action_type}: {event.src_path}")
        log.debug(f"Arquivo {action_type}: {event.src_path}")

        # Sincroniza o arquivo modificado
        file_path = event.src_path
        relative_path = os.path.relpath(os.path.dirname(file_path),
                                        local_dir)
        current_folder_id = folder_id

        # Recria a estrutura de pastas no Google Drive
        if relative_path != '.':
            for folder_name in relative_path.split(os.sep):
                current_folder_id = get_or_create_folder(folder_name,
                                                         current_folder_id)

        # Faz o upload do arquivo
        upload_file(file_path, current_folder_id)


# ID da pasta no Google Drive (substitua pelo ID da sua pasta)
folder_id = env["GDRIVE_BASE_FOLDER_ID"]

# Diretório local a ser sincronizado
local_dir = env["DESTINATION_DIR_IMAGE"]

# Arquivo local para armazenar o estado dos arquivos enviados
uploaded_files_dirs_path = 'uploaded_files_dirs.json'

# Carrega o dicionário de arquivos enviados a partir do arquivo local
if os.path.exists(uploaded_files_dirs_path):
    with open(uploaded_files_dirs_path, 'r') as f:
        uploaded_files_dirs = json.load(f)
else:
    uploaded_files_dirs = {
            "uploaded_dirs": {
                    folder_id: {}
                }
        }

if __name__ == "__main__":
    # Sincroniza o diretório local com o Google Drive ao iniciar o script
    sync_directory(local_dir, folder_id)

    # Inicia o monitoramento de mudanças no diretório local
    event_handler = SyncHandler()
    observer = Observer()
    observer.schedule(event_handler, path=local_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
