#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 21 15:27:18 2025.

@author: vcsil
"""

import logging
from logging.handlers import RotatingFileHandler


class SetupLogger():
    """
    Cria um canal de registro de ocorrencias.

    Parameters
    ----------
    log_file : str, optional
        Endereço para o arquivo de log. The default is "log.txt".
    getLogger: str, optional
        Identificado do logger.
    level : int, optional
        Level de ativaçao de registro de log. The default is logging.INFO.
    max_log_size : int, optional
        Tamanho em MB do arquivo log. The default is 5.
    backup_count : int, optional
        Quantidade de arquivos a serem criados. The default is 3.

    Returns
    -------
    None.

    """

    def __init__(self, log_file: str = "log.txt", getLogger: str = "syncDrive",
                 level: int = logging.INFO, max_log_size: int = 5,
                 backup_count: int = 3):
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logger = logging.getLogger(getLogger)
        logger.setLevel(level)
        handler = RotatingFileHandler(log_file,
                                      maxBytes=max_log_size * 1024 * 1024,
                                      backupCount=backup_count)
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)

        logger.propagate = False  # Evita que logs subam para o root logger

        self.logger = logger

        # mapa de cores ANSI
        self._colors = {
            "INFO":    "\033[36m",   # cyan
            "WARNING": "\033[33m",   # yellow
            "ERROR":   "\033[31m",   # red
            "RESET":   "\033[0m"
        }

    def _print(self, level: str, text: str, console: bool):
        if console:
            color = self._colors.get(level, "")
            reset = self._colors["RESET"]
            print(f"{color}{text}{reset}")

    def info(self, text: str, console: bool = True):
        """
        Ativa um log de nível info.

        Parameters
        ----------
        text : str
            Texto a ser registrado no log.
        console : bool, optional
            Se precisa que o log seja impresso no console. The default is True.

        Returns
        -------
        None.

        """
        self.logger.info(text)
        self._print("INFO", text, console)

    def warning(self, text: str, console: bool = True):
        """
        Ativa um log de nível warning.

        Parameters
        ----------
        text : str
            Texto a ser registrado no log.
        console : bool, optional
            Se precisa que o log seja impresso no console. The default is True.

        Returns
        -------
        None.

        """
        self.logger.info(text)
        self._print("WARNING", text, console)

    def error(self, text: str, console: bool = True):
        """
        Ativa um log de nível error.

        Parameters
        ----------
        text : str
            Texto a ser registrado no log.
        console : bool, optional
            Se precisa que o log seja impresso no console. The default is True.

        Returns
        -------
        None.

        """
        self.logger.info(text)
        self._print("ERROR", text, console)
