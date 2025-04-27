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

    def __init__(self, client_secret_path: str):
        head_path = client_secret_path.parent
        self.client_secret_path = client_secret_path
        self.settings_path = Path(head_path) / "settings.yaml"
        self.credentials_path = Path(head_path) / "credentials.json"

        self._ensure_settings_file()

        self.gauth = GoogleAuth(settings_file=self.settings_path)

    def authenticate(self):
        """Realiza autenticação, resgatando credenciais persistentes."""
        self.gauth.LoadCredentialsFile(self.credentials_path)

        # Se não houver credenciais válidas ou estiverem expiradas
        if self.gauth.credentials is None:
            # Autenticação local
            self.gauth.LocalWebserverAuth()
        elif self.gauth.access_token_expired:
            # Renova as credenciais se estiverem expiradas
            self.gauth.Refresh()
            # Salva as credenciais para uso futuro
            self.gauth.SaveCredentialsFile(self.credentials_path)
        else:
            # Inicializa com as credenciais existentes
            self.gauth.Authorize()

        return self.gauth

    def _ensure_settings_file(self):
        """Cria settings.yaml necessário para a autenticação."""
        if self.settings_path.exists():
            return                                  # já existe – nada a fazer

        settings_content = f"""client_config_backend: file
client_config_file: {self.client_secret_path}

save_credentials: True
save_credentials_backend: file
save_credentials_file: {self.credentials_path}

get_refresh_token: True

oauth_scope:
  - https://www.googleapis.com/auth/drive"""

        with open(self.settings_path, 'w') as f:
            f.write(settings_content)
