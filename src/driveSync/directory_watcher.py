#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 21 15:19:00 2025.

@author: vcsil
"""

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from collections import defaultdict
from typing import Callable
import time


class DirectoryWatcher:
    """Responsável por observar o diretório."""

    def __init__(self, path: str, on_created: Callable[[str], None],
                 logger, drive_client, obj_uploads: dict,
                 TARGET_FOLDER_ID: str, debounce_sec: float = 2.0):
        self.path = path
        self.on_created = on_created
        self.observer = Observer()

        self.logger = logger
        self.drive_client = drive_client
        self.obj_uploads = obj_uploads
        self.TARGET_FOLDER_ID = TARGET_FOLDER_ID
        self.debounce_sec = debounce_sec

        # dicionário {caminho: timestamp do último evento aceito}
        self._last_event = defaultdict(float)

    def start(self):
        """Inicia observador."""
        handler = self._make_handler()
        self.observer.schedule(handler, self.path, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        finally:
            self.observer.stop()
        self.observer.join()

    def _is_duplicate(self, file_path: str) -> bool:
        """Se o último evento ocorreu há menos que debounce_sec -> True."""
        now = time.time()
        if now - self._last_event[file_path] < self.debounce_sec:
            return True
        self._last_event[file_path] = now
        return False

    def _make_handler(self):
        watcher = self   # alias para usar dentro da classe interna

        class Handler(FileSystemEventHandler):
            def on_created(self_inner, event):
                if event.is_directory or watcher._is_duplicate(event.src_path):
                    return

                watcher.on_created(event.src_path, watcher.logger,
                                   watcher.drive_client, watcher.obj_uploads,
                                   watcher.TARGET_FOLDER_ID)

            def on_modified(self_inner, event):
                # trata modificação como “novo” upload, usando o mesmo debounce
                if event.is_directory or watcher._is_duplicate(event.src_path):
                    return
                watcher.on_created(event.src_path, watcher.logger,
                                   watcher.drive_client, watcher.obj_uploads)

        return Handler()
