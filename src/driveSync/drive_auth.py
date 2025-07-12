#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 21 14:15:43 2025.

@author: vcsil
"""

from pydrive2.auth import GoogleAuth
from pathlib import Path


class DriveAuth:
    """Realiza autenticação com o google."""

    def __init__(self, client_secrets_path: str):
        self.client_secrets_path = client_secrets_path

        head_path = client_secrets_path.parent
        self.credentials_path = Path(head_path) / "credentials.json"

        self.gauth = GoogleAuth(settings=self._ensure_settings_file())

    def authenticate(self):
        """Realiza autenticação, resgatando credenciais persistentes."""
        # Tenta carregar credenciais existentes
        self.gauth.LoadCredentialsFile(self.credentials_path)

        # Se não houver credenciais válidas ou estiverem expiradas
        if self.gauth.credentials is None:
            # Autenticação local
            self.gauth.LocalWebserverAuth()
        elif self.gauth.access_token_expired:
            # Renova as credenciais se estiverem expiradas
            self.gauth.Refresh()
        else:
            # Inicializa com as credenciais existentes
            self.gauth.Authorize()

        # Salva as credenciais para uso futuro
        self.gauth.SaveCredentialsFile(self.credentials_path)

        return self.gauth

    def _ensure_settings_file(self):
        """Cria settings.yaml necessário para a autenticação."""
        return {
            "client_config_backend": "file",
            "client_config_file": str(self.client_secrets_path),
            "save_credentials": True,
            "save_credentials_backend": "file",
            "save_credentials_file": str(self.credentials_path),
            "get_refresh_token": True,
            "oauth_scope": ["https://www.googleapis.com/auth/drive"]
        }
