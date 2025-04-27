#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 21 15:27:46 2025.

@author: vcsil
"""

from driveSync.uploaded_filesdirs import UploadedFilesDirs
from driveSync.directory_watcher import DirectoryWatcher
from driveSync.cleanup_worker import CleanupWorker
from concurrent.futures import ThreadPoolExecutor
from driveSync.logger_setup import SetupLogger
from driveSync.drive_client import DriveClient
from driveSync.retry_queue import RetryQueue
from driveSync.drive_auth import DriveAuth
from dotenv import dotenv_values
from pathlib import Path
import threading
import time
import os


def BUILD_ABSPATH(*args):
    """Constroi caminhos absolutos da raiz."""
    path = Path(__file__).parent.joinpath(*args).resolve()
    return path


executor = ThreadPoolExecutor(max_workers=4)
retry_queue = RetryQueue(BUILD_ABSPATH("../retry_queue.json"))


def retry_worker():
    """Tenta outra vez fazer upload de arquivos."""
    while True:
        item = retry_queue.pop()
        if not item:
            time.sleep(60)        # nada a fazer; espera 1 min
            continue
        try:
            # tenta novamente – reutiliza mesma função
            sync_upload(item["local_path"], logger, drive_client,
                        obj_uploads, item["parent_id"], retry_queue)
        except Exception as err:
            # se ainda falhar, re-enfileira com contador +1
            if item["retries"] + 1 < retry_queue.max_retries:
                retry_queue.add(item["local_path"],
                                item["parent_id"],
                                retries=item["retries"] + 1)
            else:
                logger.error(f"Desistindo após {retry_queue.max_retries} "
                             f"tentativas: {item['local_path']}")
                logger.error(err)
        time.sleep(5)              # evita *busy loop*


threading.Thread(target=retry_worker, daemon=True).start()


def handle_new_file(path: str, log, dclient,
                    dict_uploads: dict, folder_id: str) -> None:
    """Observador de novos arquivos."""
    executor.submit(sync_upload, path, log, dclient, dict_uploads,
                    folder_id, retry_queue)


def sync_upload(path: str, log, dclient,
                dict_uploads: dict, folder_id: str, retry_q) -> None:
    """
    Faz operações necessárias para sincronizar pastas e arquivos.

    Parameters
    ----------
    path : str
        Endereço do arquivo.
    log : TYPE
        Chamável de log.
    dclient : TYPE
        Cliente Drive.
    dict_uploads : dict
        Dict de objetos sincronizados.
    folder_id : str
        ID da folder root do drive.

    Returns
    -------
    None
        DESCRIPTION.

    """
    log.info(f"Novo arquivo detectado: {path}")

    # Sincroniza o arquivo modificado
    relative_path = Path(path).relative_to(local_dir)

    current_folder_id = folder_id

    try:
        # Recria a estrutura de pastas no Google Drive
        if relative_path != '.':
            for folder_name in relative_path.parts[:-1]:
                current_folder_id = get_or_create_folder(folder_name,
                                                         current_folder_id,
                                                         log, dclient,
                                                         dict_uploads)

        # Faz o upload do arquivo
        metadata = dclient.upload_file(path, current_folder_id)
        obj_uploads.update_last_upload(current_folder_id)

        file_size = int(metadata['fileSize']) / (1000 * 1000)
        log_txt = f"Arquivo {relative_path} ({file_size:.2f} MB) "
        log_txt += f"enviado em {metadata['uploadTime']:.2f} segundos."
        log.info(log_txt)

        try:
            os.remove(path)
            log.info(f"Arquivo local apagado: {relative_path}", False)
        except OSError as err:
            # Não interrompe o fluxo se falhar, apenas registra
            log.warning(f"Falhou para apagar {relative_path}: {err}")

    except Exception as exc:
        log.error(f"Falha mesmo após retries: {exc}")
        retry_q.add(path, current_folder_id)


def get_or_create_folder(folder_name, parent_folder_id, log, dclient,
                         dict_uploads) -> None:
    """Verifica se a pasta já existe no Google Drive. Se não existir, cria."""
    log.info(f"Verifica se a pasta {folder_name} já existe.")

    dirs = obj_uploads.uploads["uploaded_dirs"]

    # Verifica se o ID da pasta não foi salvo no arquivo de registros
    if parent_folder_id not in dirs:
        log.info("Salva ID de pasta ainda não salvo", False)
        dirs[parent_folder_id] = {}

    # Verifica se o ID da pasta já está salvo
    if folder_name in dirs[parent_folder_id]:
        log.info("ID salvo, pega no dict.", False)
        return dirs[parent_folder_id][folder_name]["id"]

    folder_list = dclient.list_folder(parent_folder_id, folder_name)
    if folder_list:
        # Adiciona ao dicionário para consultas futuras
        dict_uploads.add_dir(parent_folder_id, folder_list[0]['title'],
                             folder_list[0]["id"])

        log.info("Pasta existe. Adicionando ao arquivo de registros.")
        return folder_list[0]['id']  # Retorna o ID da pasta existente
    else:
        # Cria uma nova pasta
        folder = dclient.create_folder(folder_name, parent_folder_id)
        dict_uploads.add_dir(parent_folder_id, folder['title'], folder["id"])

        log.info("Pasta não existe. Cria/adiciona no arquivo de registros.")
        return folder["id"]


if __name__ == "__main__":
    env = dotenv_values(BUILD_ABSPATH("..", ".env"))

    # Inicia logger
    logger = SetupLogger(BUILD_ABSPATH("../logs/log-drive.txt"), "syncDrive")

    # Inicia conexao e autenticacao com o drive
    client_secret_path = BUILD_ABSPATH(
        "../credentials-google/client_secret.json")
    auth = DriveAuth(client_secret_path).authenticate()

    # Inicia cliente do drive
    drive_client = DriveClient(auth)

    # Lê arquivo que armazena informações do que já foi sincronizado
    obj_uploads = UploadedFilesDirs(BUILD_ABSPATH("../uploads.json"))

    local_dir = BUILD_ABSPATH("..", env["DESTINATION_DIR_IMAGE"])
    watcher = DirectoryWatcher(path=local_dir, on_created=handle_new_file,
                               logger=logger, drive_client=drive_client,
                               obj_uploads=obj_uploads,
                               TARGET_FOLDER_ID=env["GDRIVE_BASE_FOLDER_ID"])

    # Exclui arquivos que não foram atualizados a mais de 15 dias
    cleanup = CleanupWorker(drive_client, obj_uploads, logger,
                            limite_dias=15, intervalo_horas=24)
    cleanup.start()

    try:
        logger.info("Iniciando observação de diretório.")
        watcher.start()
    finally:
        obj_uploads.update_dict()
