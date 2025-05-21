# -*- coding: utf-8 -*-
"""
Created on Sat Feb  8 16:32:24 2025.

@author: vinic
"""
from typing import Union, Optional
from dotenv import dotenv_values
from datetime import datetime
import pytesseract as tess
from pathlib import Path
from tqdm import tqdm
import numpy as np
import subprocess
import tempfile
import shutil
import cv2
import re
import os

from utils.utils import BUILD_ABSPATH, file_root_recursive

env = dotenv_values()

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
VIDEO_SUFFIXES = {".mp4", ".avi", ".mkv", ".mov"}
URL_RE = re.compile(
    r"\b[\w-]+(?:\.[\w-]+)*\.(?:com|net|org|me|cc|vip|win|bet|pro)\b",
    flags=re.I)

# Diretório base onde as mídias estão armazenadas
BASE_MEDIA_DIR = BUILD_ABSPATH(__file__, "..", env["FIRST_DONWLOAD_FOLDER"])

# Diretório base para onde as mídias serão movidas
BASE_DESTINATION_DIR = BUILD_ABSPATH(__file__,
                                     "..", env["DESTINATION_DIR_IMAGE"])


def extract_urls(img: np.ndarray) -> list[str]:
    """Extrai urls da imagem."""
    # Extrair texto da imagem
    custom_config = r'--oem 3 --psm 11 --dpi 300'
    text = tess.image_to_string(img, config=custom_config)

    return URL_RE.findall(text)


def crop_image_percentage(imagem: np.ndarray) -> list[np.ndarray]:
    """
    Retorna os 1 primeiros e os 3 últimos 10% da imagem.

    Parameters
    ----------
    imagem : TYPE
        Array NumPy representando a imagem.

    Returns
    -------
    cortes : TYPE
        Uma lista contendo os cortes da imagem.

    """
    altura, largura = imagem.shape[:2]  # Obtém as dimensões da imagem

    # Lista para armazenar os cortes
    cortes = []

    # Pega primeiros 10%
    for i in range(1):
        inicio = int(i * 0.11 * altura)
        fim = int((i + 1) * 0.11 * altura)
        corte = imagem[inicio:fim, :]  # Corta a imagem na altura especificada
        cortes.append(corte)

    # Pega os último 15%
    for i in range(1):
        inicio = int(8.5 * 0.1 * altura)
        fim = int((8.5 + 1) * 0.1 * altura)
        corte = imagem[inicio:fim, :]  # Corta a imagem na altura especificada
        cortes.append(corte)

    return cortes


def retorna_contornos(image: np.ndarray):
    """Desenha contornos na imagem."""
    altura, largura = image.shape  # Obtém dimensões da imagem

    # Aumentar contraste usando equalização de histograma
    equalized = cv2.equalizeHist(image)

    # Binarização da imagem para melhorar o OCR
    _, binary = cv2.threshold(equalized, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Encontrar contornos
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    # Encontrar o maior contorno válido
    c = max(contours, key=cv2.contourArea)

    # Obter a bounding box do maior contorno válido
    x, y, w, h = cv2.boundingRect(c)

    # Ignora caixa muito pequenas
    if w < 100:
        return None

    # Recortar a região detectada
    cropped = image[y:y+h, x:x+w]

    return cropped, contours


def process_image(image: np.ndarray, log) -> Union[str, False]:
    """Faz transformações na imagem para buscar URL."""
    if image is None:
        log.error(f"Não foi possível carregar a imagem: {image}")
        return

    # Redimensionar a imagem para aumentar a resolução
    scale_percent = 200  # Aumenta a resolução em 200%
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)
    dim = (width, height)
    resized = cv2.resize(image, dim, interpolation=cv2.INTER_LINEAR)

    # Converter para escala de cinza
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # Aplicar um filtro para melhorar o contraste
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Pegar as partes de interesse da imagem, cortes finais e iniciais
    for corte in crop_image_percentage(blurred):

        img_cropped = retorna_contornos(corte)

        # Pula se não encontrar bordas utils
        if img_cropped is None:
            continue

        img_cropped = img_cropped[0].copy()

        # Aplicar operações morfológicas para destacar o texto
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        img_dilated = cv2.dilate(img_cropped, kernel, iterations=1)

        img_eroded = cv2.erode(img_dilated, kernel, iterations=1)

        # Procurar URLs no texto extraído
        matches = extract_urls(img_eroded)
        if matches:
            return matches

    return False


# Função para capturar o primeiro quadro de um vídeo
def get_first_frame(video_path: Path, log) -> np.ndarray:
    """
    Extrai o primeiro frame de um vídeo e retorna como array NumPy.

    Args
    ----
    video_path: Caminho para o arquivo de vídeo

    Returns
    -------
    np.ndarray: Array NumPy contendo o primeiro frame do vídeo

    Raises
    ------
    FileNotFoundError: Se o arquivo de vídeo não existir
    RuntimeError: Se ocorrer um erro durante a extração do frame
    """
    # Verificação do arquivo de entrada
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(
            f"O arquivo de vídeo '{video_path}' não foi encontrado")

    # Estratégia 1: Se falhar, usar FFmpeg como fallback (mais compatível)
    frame = _try_ffmpeg_extraction(video_path, log)

    # Estratégia 2: Tentar OpenCV diretamente (mais rápido quando funciona)
    if frame is None:
        frame = _try_opencv_extraction(video_path, log)

    # Se ainda não tivermos um frame, falhar com erro significativo
    if frame is None:
        raise RuntimeError(
            "Não foi possível extrair frame usando os métodos disponíveis. "
            "Verifique se o vídeo está corrompido ou em formato não suportado."
        )

    return frame


def _try_ffmpeg_extraction(video_path: Path, log) -> Optional[np.ndarray]:
    """Extrai o primeiro frame usando FFmpeg e retorna como numpy array."""
    try:
        # Criar arquivo temporário para o frame extraído
        with tempfile.NamedTemporaryFile(suffix='.png',
                                         delete=False) as temp_file:
            temp_path = temp_file.name

        # Comando otimizado para extrair apenas o primeiro frame
        command = [
            "ffmpeg",
            "-ss", "0",  # Posição inicial
            "-i", str(video_path),
            "-vframes", "1",  # Apenas um frame
            "-q:v", "1",  # Máxima qualidade
            "-f", "image2",  # Formato de saída
            "-an",  # Sem áudio
            "-y",  # Sobrescrever sem perguntar
            temp_path
        ]

        # Executar FFmpeg
        subprocess.run(command, capture_output=True, text=True)

        # Ler a imagem gerada
        frame = cv2.imread(temp_path)

        # Remover arquivo temporário
        try:
            os.unlink(temp_path)
        except Exception:
            pass

        return frame

    except Exception as e:
        log.warning(f"Extração com FFmpeg falhou: {e}")
        return None


def _try_opencv_extraction(video_path: Path, log) -> Optional[np.ndarray]:
    """Tenta extrair o primeiro frame usando OpenCV diretamente."""
    try:
        cap = cv2.VideoCapture(str(video_path))

        if cap.isOpened():
            # Configurar para decodificar apenas o 1 frame (mais rápido)
            cap.set(cv2.CAP_PROP_FRAME_COUNT, 1)
            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                return frame
    except Exception as e:
        log.debug(f"Tentativa OpenCV falhou: {e}")

    return None


def move_file(src: Path, midia_date, urls: list[str], log) -> None:
    """Move arquivo para outro diretório."""
    month = midia_date.strftime("%m-%Y")
    domain = urls[0] if urls else "others" / midia_date.strftime("%Y-%m-%d")
    target = BUILD_ABSPATH("../..", env["DESTINATION_DIR_IMAGE"],
                           month, domain)
    target.mkdir(parents=True, exist_ok=True)
    shutil.move(src, target / src.name)

    log.info(f"Arquivo movido para: {target}")


def organize_midia(file_path: str, file_date: datetime, log) -> None:
    """Move imagem para diretório correspondente a URL."""
    file_path = Path(file_path)
    # Verificar se o arquivo é uma imagem ou vídeo
    if file_path.suffix.lower() in IMAGE_SUFFIXES:
        image = cv2.imread(file_path)

    elif file_path.suffix.lower() in VIDEO_SUFFIXES:
        image = get_first_frame(file_path, log)

    else:
        # Ignorar arquivos que não são imagens ou vídeos
        log.info(f"Ignorando arquivo não suportado: {file_path}")
        return

    matches = process_image(image, log)

    move_file(file_path, file_date, matches, log)


def main():
    """Percorre por todas os arquivos com sufixo especificado na pasta."""
    from utils.logger_setup import SetupLogger
    from datetime import timedelta, timezone

    logger = SetupLogger(BASE_MEDIA_DIR.parent / "log-organize.txt",
                         "organize")

    # UTC-3
    tz = timezone(timedelta(hours=-3))

    files = file_root_recursive(BASE_MEDIA_DIR)

    for file in tqdm(files):
        organize_midia(file, datetime.now(tz), logger)


# Executa o script
if __name__ == "__main__":
    main()
