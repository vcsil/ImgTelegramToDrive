#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 20:51:04 2025.

@author: vcsil
"""

from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential, before_sleep_log)
from pydrive2.files import ApiRequestError   # qualquer exceção HTTP da API
import logging
import socket                                # para erros de rede

logger = logging.getLogger("syncDrive")


def api_retry(max_attempts: int = 5):
    """Retry exponencial para chamadas à API."""
    return retry(
        reraise=True,  # devolve a exceção se esgotar
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((
            ApiRequestError,               # 4xx/5xx do Google
            socket.gaierror,               # DNS/network
            ConnectionResetError,
            TimeoutError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
