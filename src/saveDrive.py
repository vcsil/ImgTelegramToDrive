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
import sys
import os


def BUILD_ABSPATH(*args):
    """Constroi caminhos absolutos da raiz."""
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), *args)
    )
    return path


env = dotenv_values()

# Configuração do logging
log_file = BUILD_ABSPATH("..", "logs", "log-drive.txt")  # Nome do arquivo
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
        return record.levelno == logging.DEBUG


# Adiciona o filtro ao handler padrão
for handler in logging.root.handlers:
    handler.addFilter(OnlyErrorFilter())

log = logging.getLogger('root')


class GoogleDriveManager:
    """Gerencia a conexão com o Google Drive."""

    def __init__(self, credentials_folder="credentials-google"):
        """
        Inicializa o gerenciador do Google Drive.

        Parameters
        ----------
        credentials_folder : str opcional
            DESCRIPTION. Pasta que serão armazenados os arquivos de credenciais

        Returns
        -------
        None.

        """
        self.credentials_folder = BUILD_ABSPATH("..", credentials_folder)
        # Cria a pasta de credenciais se não existir
        os.makedirs(self.credentials_folder, exist_ok=True)

        self.settings_path = os.path.join(self.credentials_folder,
                                          "settings.yaml")
        self.creds_path = os.path.join(self.credentials_folder,
                                       "credentials.json")
        self.client_secret = os.path.join(self.credentials_folder,
                                          "client_secret.json")

        self.drive = None
        self._ensure_settings_file()
        self.authenticate()

    def authenticate(self):
        """Autentica com o Google Drive e persiste a conexão."""
        self.gauth = GoogleAuth(settings_file=self.settings_path)

        try:
            # Carrega as credenciais salvas
            self.gauth.LoadCredentialsFile(self.creds_path)

            # Se não houver credenciais válidas ou estiverem expiradas
            if self.gauth.credentials is None:
                # Autenticação local
                self.gauth.CommandLineAuth()
            elif self.gauth.access_token_expired:
                # Renova as credenciais se estiverem expiradas
                self.gauth.Refresh()
            else:
                # Inicializa com as credenciais existentes
                self.gauth.Authorize()

            # Salva as credenciais para uso futuro
            self.gauth.SaveCredentialsFile(self.creds_path)

            # Inicializa o cliente do Google Drive
            self.drive = GoogleDrive(self.gauth)
            log.info("Autenticação válida")
            print("Autenticação com o Google Drive realizada com sucesso!")

        except Exception as e:
            log.error(f"Erro ao carregar credenciais: {e}")
            print(f"Erro na autenticação: {e}")
            sys.exit(1)

    def _ensure_settings_file(self):
        """Cria settings.yaml necessário para a autenticação."""
        if os.path.exists(self.settings_path):
            return                                  # já existe – nada a fazer

        settings_content = f"""client_config_backend: file
client_config_file: {self.client_secret}

save_credentials: True
save_credentials_backend: file
save_credentials_file: {self.creds_path}

get_refresh_token: True

oauth_scope:
  - https://www.googleapis.com/auth/drive"""

        with open(self.settings_path, 'w') as f:
            f.write(settings_content)

        print(f"⚙ settings.yaml criado em {self.settings_path}")

    def upload_file(self, file_path: str, parent_folder_id: str):
        """
        Faz o upload de um arquivo para o Google Drive.

        Parameters
        ----------
        file_path : str
            Caminho do arquivo local.
        parent_folder_id : str
            ID da pasta onde o arquivo será salvo (opcional).

        Returns
        -------
        None.

        """
        start_time = datetime.datetime.now()
        file_name = os.path.basename(file_path)

        # Cria um objeto de arquivo do Google Drive
        gfile = self.drive.CreateFile({'title': file_name,
                                       'parents': [{'id': parent_folder_id}]})

        # Define o conteúdo do arquivo
        gfile.SetContentFile(file_path)

        # Faz o upload do arquivo
        gfile.Upload()
        end_time = datetime.datetime.now()

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        log_txt = f"Arquivo {file_name} ({file_size:.2f} MB) enviado em "
        log_txt += f"{(end_time - start_time).total_seconds():.2f} segundos."
        log.info(log_txt)
        return

    def create_folder(self, folder_name: str, parent_folder_id: str):
        """
        Cria uma pasta no Google Drive.

        Parameters
        ----------
        folder_name : str
            Nome da pasta a ser criada.
        parent_folder_id : str
            Objeto da pasta criada no Google Drive.

        Returns
        -------
        folder : files.GoogleDriveFile
            folder criado

        """
        # Cria um objeto de pasta do Google Drive
        folder_metadata = {
            'title': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [{'id': parent_folder_id}]
        }

        log.info(f"Cria o diretório {folder_name} no Drive")
        folder = self.drive.CreateFile(folder_metadata)
        folder.Upload()

        print(f"Pasta '{folder_name}' criada com sucesso no Google Drive!")
        return folder

    def list_files(self, folder_id: str = "root", query: str = ""):
        """
        Lista arquivos/pastas no Google Drive.

        Parameters
        ----------
        folder_id : str, optional
            ID da pasta para listar seu conteúdo. The default is "root".
        query : str, optional
            Consulta personalizada para filtrar resultados. The default "".

        Returns
        -------
        TYPE
            Lista de arquivos/pastas.

        """
        if folder_id:
            if query:
                query += f" and '{folder_id}' in parents and trashed=false"
            else:
                query = f"'{folder_id}' in parents and trashed=false"

        file_list = self.drive.ListFile({'q': query}).GetList()
        return file_list

    def print_file_list(self, file_list: list):
        """
        Exibe uma lista formatada de arquivos/pastas.

        Parameters
        ----------
        file_list : list
            Lista de arquivos/pastas.

        Returns
        -------
        None.

        """
        if not file_list:
            print("Nenhum arquivo encontrado.")
            return

        print("ID | Nome | Tipo")
        print("-" * 50)

        for file in file_list:
            file_type = (
                "Pasta"
                if file['mimeType'] == 'application/vnd.google-apps.folder'
                else "Arquivo")

            print(f"{file['id']} | {file['title']} | {file_type}")


drive = GoogleDriveManager()


class UploadedFilesDirs:
    """Lida com o arquivo que armazena os arquivos/diretorio sincronizados."""

    def __init__(self):
        # Arquivo local para armazenar o estado dos arquivos enviados
        self.uploaded_files_dirs_path = BUILD_ABSPATH("..", "uploads.json")

        # Carrega o dicionário de arquivos enviados a partir do arquivo local
        if os.path.exists(self.uploaded_files_dirs_path):
            with open(self.uploaded_files_dirs_path, 'r') as f:
                self.uploads = json.load(f)
        else:
            self.uploads = {
                    "uploaded_dirs": {
                            folder_id: {}
                        }
                }

    def add_dir(self, parent_id: str, folder_name: str, folder_id: str):
        """
        Salva um diretório que foi sincronizado.

        Parameters
        ----------
        parent_id : str
            ID da diretorio pai.
        folder_name : str
            Nome do diretorio criado
        folder_id : str
            ID do diretorio criado.

        Returns
        -------
        None.

        """
        if folder_id not in self.uploads["uploaded_dirs"]:
            self.uploads["uploaded_dirs"]["folder_id"] = folder_id

        self.uploads["uploaded_dirs"][parent_id][folder_name] = folder_id
        return

    def add_file(self, file_name: str):
        """
        Salva um arquivo que foi sincronizado.

        Parameters
        ----------
        file_name : str
            Nome do arquvio subido.

        Returns
        -------
        None.

        """
        self.uploads[file_name] = True  # Marca o arquivo como enviado

        return

    def update_dict(self):
        """Atualiza e salva o arquivo com as mudanças."""
        with open(self.uploaded_files_dirs_path, 'w') as f:
            json.dump(self.uploads, f)

        return


def get_or_create_folder(folder_name, parent_folder_id):
    """Verifica se a pasta já existe no Google Drive. Se não existir, cria."""
    log.info(f"Verifica se a pasta {folder_name} já existe no Google Drive")

    if parent_folder_id not in obj_uploads.uploads["uploaded_dirs"]:
        obj_uploads.uploads["uploaded_dirs"][parent_folder_id] = {}

    if folder_name in obj_uploads.uploads["uploaded_dirs"][parent_folder_id]:
        return (obj_uploads.uploads["uploaded_dirs"]
                [parent_folder_id][folder_name])

    query = f"'{parent_folder_id}' in parents and title='{folder_name}' "
    query += "and mimeType='application/vnd.google-apps.folder' "
    query += "and trashed=false"
    folder_list = drive.drive.ListFile({'q': query}).GetList()
    if folder_list:
        # Adiciona ao dicionário para consultas futuras
        obj_uploads.add_dir(parent_folder_id, folder_list[0]['title'],
                            folder_list[0]["id"])
        return folder_list[0]['id']  # Retorna o ID da pasta existente
    else:
        # Cria uma nova pasta
        folder = drive.create_folder(folder_name, parent_folder_id)
        obj_uploads.add_dir(parent_folder_id, folder['title'], folder["id"])
        return folder["id"]


def file_already_uploaded(file_name, parent_folder_id):
    """Verifica se arquivo já foi para a pasta especificada Drive."""
    # Verifica primeiro no dicionário local
    if file_name in obj_uploads.uploads:
        return True

# =============================================================================
#     # Faz verificação no drive
#     query = f"'{parent_folder_id}' in parents and title='{file_name}' "
#     query += "and trashed=false"
#     file_list = drive.drive.ListFile({'q': query}).GetList()
#
#     if file_list:
#         # Adiciona ao dicionário para consultas futuras
#         obj_uploads.add_file(file_name)  # Salva o dicionário atualizado
#         log.info(f'Arquivo {file_name} já existe no Google Drive.Ignorando.')
#         return True
# =============================================================================
    return False


def sync_directory(local_path, drive_parent_folder_id):
    """Sincroniza um diretório local no Google Drive, mantendo a estrutura."""
    # Lista todos os arquivos para exibir uma barra de progresso geral
    all_files = []
    for root, _, files in os.walk(local_path):
        all_files.extend([os.path.join(root, file) for file in files])

    files_not_uploaded = [file_path for file_path in all_files
                          if file_path
                          not in obj_uploads.uploads]

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

                    if not file_already_uploaded(file_path, current_folder_id):
                        drive.upload_file(file_path, current_folder_id)
                        obj_uploads.add_file(file_path)

                        pbar.update(1)  # Atualiza a barra de progresso


class SyncHandler(FileSystemEventHandler):
    """Observa alteracoes no diretorio especifico."""

    def on_created(self, event):
        """Acionado quando objeto e criado."""
        self.process_event(event, "criado")

    def on_moved(self, event):
        """Acionado quando objeto e movido."""
        self.process_event(event, "movido")

    def on_modified(self, event):
        """Acionado quando objeto e modificado."""
        self.process_event(event, "modificado")

    def process_event(self, event, action_type):
        """Vai processar arquivos novos."""
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
        drive.upload_file(file_path, current_folder_id)
        obj_uploads.add_file(file_path)


if __name__ == "__main__":
    # ID da pasta no Google Drive
    folder_id = env["GDRIVE_BASE_FOLDER_ID"]

    # Diretório local a ser sincronizado
    local_dir = BUILD_ABSPATH("..", env["DESTINATION_DIR_IMAGE"])

    obj_uploads = UploadedFilesDirs()

    try:
        # Sincroniza o diretório local com o Google Drive ao iniciar o script
        sync_directory(local_dir, folder_id)

        # Inicia o monitoramento de mudanças no diretório local
        event_handler = SyncHandler()
        observer = Observer()
        observer.schedule(event_handler, path=local_dir, recursive=True)
        observer.start()

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    finally:
        obj_uploads.update_dict()

    observer.join()
