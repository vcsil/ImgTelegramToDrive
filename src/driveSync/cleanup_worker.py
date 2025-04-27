#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 23 19:34:40 2025.

@author: vcsil
"""
import threading
import time


class CleanupWorker(threading.Thread):
    """Move para a lixeira pastas sem uploads há >= limite_dias."""

    def __init__(self, drive_client, uploaded_dirs, logger,
                 limite_dias: int = 15, intervalo_horas: int = 24):
        super().__init__(daemon=True)
        self.drive_client = drive_client
        self.uploaded_dirs = uploaded_dirs   # instância de UploadedFilesDirs
        self.logger = logger
        self.limite_seg = limite_dias * 24 * 3600
        self.intervalo_seg = intervalo_horas * 3600

    def run(self):
        """Ativa o timer para aguardar."""
        while True:
            self._varrer()
            time.sleep(self.intervalo_seg)

    def _varrer(self):
        agora = time.time()
        dirs_para_lixeira = []

        for parent, children in list(
                self.uploaded_dirs.uploads["uploaded_dirs"].items()):
            for folder_name, meta in list(children.items()):
                if agora - meta["last_upload"] >= self.limite_seg:
                    dirs_para_lixeira.append((parent, folder_name, meta["id"]))

        for parent, folder_name, folder_id in dirs_para_lixeira:
            try:
                self.drive_client.trash_folder_recursive(folder_id)
                self.logger.info(f"Pasta '{folder_name}' (id={folder_id}) "
                                 f"> 15 dias sem uso → enviada à lixeira")
                # remove do dicionário para não processar de novo
                del (self.uploaded_dirs.uploads["uploaded_dirs"][parent]
                     [folder_name])
            except Exception as exc:
                self.logger.error(
                    f"Erro ao mover '{folder_name}' p/ lixeira: {exc}")

        if dirs_para_lixeira:
            self.uploaded_dirs.update_dict()   # salva mudanças em disco
