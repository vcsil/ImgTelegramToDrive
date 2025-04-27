#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 21 14:19:51 2025.

@author: vcsil
"""

from driveSync.retry_policies import api_retry
from pydrive2.drive import GoogleDrive
from typing import Optional, List
import datetime


class DriveClient:
    """Realiza operações no drive."""

    def __init__(self, gauth):
        """Inicia cliente do drive."""
        self.drive = GoogleDrive(gauth)

    @api_retry()
    def list_folder(self, folder_id: str = "root",
                    folder_name: str = "root") -> List[dict]:
        """
        Lista arquivos/pastas no Google Drive.

        Parameters
        ----------
        folder_id : str, optional
            ID da pasta para listar seu conteúdo. The default is "root".
        folder_name : str, optional
            Nome da pasta. The default is "root".

        Returns
        -------
        List[dict]
            Lista de arquivos/pastas.

        """
        query = f"'{folder_id}' in parents and title='{folder_name}' "
        query += "and mimeType='application/vnd.google-apps.folder' "
        query += "and trashed=false"
        return self.drive.ListFile({'q': query}).GetList()

    def print_file_list(self, file_list: list) -> None:
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

    @api_retry()
    def upload_file(self, local_path: str,
                    parent_id: Optional[str] = None) -> dict:
        """
        Faz o upload de um arquivo para o Google Drive.

        Parameters
        ----------
        local_path : str
            Caminho do arquivo local.
        parent_id : Optional[str], optional
            ID da pasta onde o arquivo será salvo (opcional). The default None.

        Returns
        -------
        dict
            DESCRIPTION.

        """
        # Cria um objeto de arquivo do Google Drive
        gfile = self.drive.CreateFile({'parents': [{'id': parent_id}]}
                                      if parent_id else {})
        # Define o conteúdo do arquivo
        gfile.SetContentFile(local_path)

        # Faz o upload do arquivo
        start_time = datetime.datetime.now()
        gfile.Upload()
        end_time = datetime.datetime.now()

        gfile.metadata["uploadTime"] = (end_time - start_time).total_seconds()

        return gfile.metadata

    @api_retry()
    def create_folder(self, name: str,
                      parent_id: Optional[str] = None) -> dict:
        """
        Cria uma pasta no Google Drive.

        Parameters
        ----------
        name : str
            Nome da pasta a ser criada.
        parent_id : Optional[str], optional
            Objeto da pasta criada no Google Drive. The default is None.

        Returns
        -------
        dict
            folder criado.

        """
        # Cria um objeto de pasta do Google Drive
        folder = self.drive.CreateFile({
            'title': name,
            'mimeType': 'application/vnd.google-apps.folder',
            **({'parents': [{'id': parent_id}]} if parent_id else {})
        })
        folder.Upload()
        return folder.metadata

    def trash_item(self, file_id: str) -> None:
        """Envia um item para a lixeira."""
        gfile = self.drive.CreateFile({'id': file_id})
        gfile.Trash()                       # 1 chamada HTTP
        return

    def trash_folder_recursive(self, folder_id: str) -> None:
        """Envia o conteúdo de uma pasta para a lixeira."""
        # Lista todos os filhos (máx = 1000 por request → GetList() já pagina)
        children = self.drive.ListFile({
            'q': f"'{folder_id}' in parents and trashed=false"
        }).GetList()

        for child in children:
            if child['mimeType'] == 'application/vnd.google-apps.folder':
                self.trash_folder_recursive(child['id'])
            else:
                self.trash_item(child['id'])

        # por último, a própria pasta
        self.trash_item(folder_id)
