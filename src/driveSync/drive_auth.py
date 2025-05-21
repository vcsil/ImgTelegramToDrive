#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 21 14:15:43 2025.

@author: vcsil
"""

from pydrive2.auth import GoogleAuth


class DriveAuth:
    """Realiza autenticação com o google."""

    def __init__(self, service_account_path: str):
        self.service_account_path = service_account_path

        self.gauth = GoogleAuth(settings=self._ensure_settings_file())

    def authenticate(self):
        """Realiza autenticação, resgatando credenciais persistentes."""
        self.gauth.ServiceAuth()
        return self.gauth

    def _ensure_settings_file(self):
        """Cria settings.yaml necessário para a autenticação."""
        return {
            "client_config_backend": "service",
            "service_config": {
                "client_json_file_path": f"{self.service_account_path}",
            }
        }
