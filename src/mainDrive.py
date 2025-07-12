#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 21 15:27:46 2025.

@author: vcsil
"""
from dotenv import dotenv_values
from pathlib import Path
import os

from utils.utils import BUILD_ABSPATH, file_root_recursive
from driveSync.uploaded_filesdirs import UploadedFilesDirs
from driveSync.drive_client import DriveClient
from driveSync.drive_auth import DriveAuth
from utils.logger_setup import SetupLogger


def sync_upload(path: str, log, dclient, local_path: Path,
                dict_uploads: dict, folder_id: str) -> None:
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
    relative_path = Path(path).relative_to(local_path)

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
        dict_uploads.update_last_upload(current_folder_id)

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


def get_or_create_folder(folder_name, parent_folder_id, log, dclient,
                         dict_uploads) -> None:
    """Verifica se a pasta já existe no Google Drive. Se não existir, cria."""
    log.info(f"Verifica se a pasta {folder_name} já existe.")

    dirs = dict_uploads.uploads["uploaded_dirs"]

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
    from tqdm import tqdm

    env = dotenv_values(BUILD_ABSPATH(__file__, "..", ".env"))

    # Inicia logger
    logger = SetupLogger(BUILD_ABSPATH(__file__,
                                       "../logs/log-drive.txt"), "syncDrive")

    # Inicia conexao e autenticacao com o drive
    client_secrets_path = BUILD_ABSPATH(
        __file__, "../credentials/client_secrets.json")
    auth = DriveAuth(client_secrets_path).authenticate()

    # Inicia cliente do drive
    drive_client = DriveClient(auth)

    # Lê arquivo que armazena informações do que já foi sincronizado
    obj_uploads = UploadedFilesDirs(BUILD_ABSPATH(__file__, "../uploads.json"))

    local_dir = BUILD_ABSPATH(__file__, "..", env["DESTINATION_DIR_IMAGE"])

    files = file_root_recursive(local_dir)

    for file in tqdm(files):
        sync_upload(file, logger, drive_client, local_dir, obj_uploads,
                    env["GDRIVE_BASE_FOLDER_ID"])

    try:
        logger.info("Iniciando observação de diretório.")
    finally:
        obj_uploads.update_dict()
