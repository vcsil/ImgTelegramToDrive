#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 21:15:42 2025.

@author: vcsil
"""

from pathlib import Path
import json
import time


class RetryQueue:
    """Guarda arquivos que falharam e tenta reenviá-los mais tarde."""

    def __init__(self, path: Path = Path("../retry_queue.json"),
                 max_retries: int = 5):
        self.path = path
        self.max_retries = max_retries
        self.queue = self._load()

    # ---------- API pública ----------
    def add(self, local_path: str, parent_id: str, retries: int = 0):
        """Adiciona arquvio a fila de reenvio."""
        self.queue.append({
            "local_path": local_path,
            "parent_id": parent_id,
            "retries": retries,
            "last_try": int(time.time())
        })
        self._save()

    def pop(self):
        """Remove e devolve o primeiro item ou None se vazio."""
        if not self.queue:
            return None
        item = self.queue.pop(0)
        self._save()
        return item

    def _load(self):
        if self.path.exists():
            with open(self.path) as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.queue, f, indent=2)
