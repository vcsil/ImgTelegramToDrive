#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May  4 14:39:42 2025.

@author: vcsil
"""
from pathlib import Path


def BUILD_ABSPATH(root, *args):
    """Constroi caminhos absolutos da raiz."""
    path = Path(root).parent.joinpath(*args).resolve()
    return path


def file_root_recursive(root_dir: Path) -> list[Path]:
    """
    Busca arquivos de mídia recursivamente a partir do root.

    Parameters
    ----------
    root_dir : Path
        Path do diretório raiz a se buscar os arquivos.

    Returns
    -------
    files : list[str]
        Lista com o endereço de todas os arquvios de imagem.

    """
    IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
    VIDEO_SUFFIXES = {".mp4", ".avi", ".mkv", ".mov"}

    files = [p for p in root_dir.rglob("*")
             if p.suffix.lower() in (*IMAGE_SUFFIXES, *VIDEO_SUFFIXES)]

    return files


def create_directory(path: Path):
    """Cria diretórios que não existem."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
