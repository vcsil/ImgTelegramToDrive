#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 16:40:12 2025.

@author: vcsil
"""
from pathlib import Path
import json
import time


class UploadedFilesDirs:
    """Lida com o arquivo que armazena os arquivos/diretorio sincronizados."""

    def __init__(self, path: str = Path("../uploads.json")):
        # Arquivo local para armazenar o estado dos arquivos enviados
        self.uploaded_files_dirs_path = path

        # Carrega o dicionário de arquivos enviados a partir do arquivo local
        if self.uploaded_files_dirs_path.exists():
            with open(self.uploaded_files_dirs_path, 'r') as f:
                self.uploads = json.load(f)
        else:
            self.uploads = {
                    "uploaded_dirs": {}
                }

    def add_dir(self, parent_id: str, folder_name: str, folder_id: str):
        """
        Salva um diretório o que foi sincronizado.

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
        dirs = self.uploads["uploaded_dirs"]

        # cria o dicionário do pai se ainda não existir
        dirs.setdefault(parent_id, {})

        # salva/atualiza a referência
        dirs[parent_id][folder_name] = {
            "id": folder_id,
            "last_upload": time.time()
        }
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

    def update_last_upload(self, folder_id: str):
        """Marca 'folder_id' como atualizado AGORA."""
        now = time.time()
        for parent, children in self.uploads["uploaded_dirs"].items():
            for meta in children.values():
                if meta["id"] == folder_id:
                    meta["last_upload"] = now
                    return
