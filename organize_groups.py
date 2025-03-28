# -*- coding: utf-8 -*-
"""
Created on Sat Feb  8 16:32:24 2025.

@author: vinic
"""
# =============================================================================
# from IPython.display import display, Image
# =============================================================================
from dotenv import dotenv_values
from datetime import datetime
from tqdm import tqdm
import pytesseract
import logging
import shutil
import cv2
import os
import re

env = dotenv_values()

log = logging.getLogger('root')


# Função para criar diretórios se não existirem
def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)


def cortar_imagem_porcentagem(imagem):
    """
    Retorna os 1 primeiros e os 3 últimos 10% da imagem.

    :param imagem: Array NumPy representando a imagem.
    :return: Uma lista contendo os cortes da imagem.
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


def retorna_contornos(image):
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


# Função para processar uma imagem
def process_image(image):
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
    for corte in cortar_imagem_porcentagem(blurred):

        cropped = retorna_contornos(corte)

        # Pula se não encontrar bordas utils
        if cropped is None:
            continue

# =============================================================================
#         # Criar uma cópia da imagem original para desenhar os contornos
#         image_contours = cv2.cvtColor(corte, cv2.COLOR_GRAY2BGR)
#         # Desenhar todos os contornos na imagem (cor verde)
#         cv2.drawContours(image_contours, cropped[1], -1, (0, 255, 0), 2)
#         plot_image(image_contours)
# =============================================================================

        cropped = cropped[0].copy()

        # Aplicar operações morfológicas para destacar o texto
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(cropped, kernel, iterations=1)

        eroded = cv2.erode(dilated, kernel, iterations=1)

        # Extrair texto da imagem
        custom_config = r'--oem 3 --psm 11 --dpi 300'
        text = pytesseract.image_to_string(eroded, config=custom_config)

        # Expressão regular para identificar URLs
        url_pattern = re.compile(
            r'\b[\w-]+(?:\.[\w-]+)*\.(?:com|net|win|cc|vip|me|org|bet|pro)\b')

        # Procurar URLs no texto extraído
        matches = url_pattern.findall(text)
        if matches:
            return matches

    return False


# Função para capturar o primeiro quadro de um vídeo
def get_first_frame(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"Não foi possível abrir o vídeo: {video_path}")

    ret, frame = cap.read()
    if not ret:
        raise Exception(
            f"Não foi possível capturar o first frame do vídeo: {video_path}")

    cap.release()
    return frame


# Função para gerar um nome de arquivo único baseado no índice
def generate_unique_filename(destination_dir, extension):
    # Contar quantos arquivos já existem no diretório
    existing_files = [f for f in os.listdir(destination_dir)
                      if os.path.isfile(os.path.join(destination_dir, f))]
    # O próximo índice será o número de arquivos existentes
    index = len(existing_files)
    return f"{index}{extension}"


# =============================================================================
# def plot_image(image):
#     _, encoded_image = cv2.imencode('.png', image)
#     display(Image(data=encoded_image.tobytes()))
#     return
# =============================================================================


def organize_image(file_name):
    # Obter o mês e ano atual no formato MM-YYYY
    current_month_year = datetime.now().strftime("%m-%Y")

    # Verificar se o arquivo é uma imagem ou vídeo
    if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp',
                                   '.gif')):
        # É uma imagem
        image = cv2.imread(file_name)
        matches = process_image(image)
    elif file_name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        # É um vídeo, capturar o primeiro quadro
        image = get_first_frame(file_name)
        matches = process_image(image)
    else:
        # Ignorar arquivos que não são imagens ou vídeos
        log.info(f"Ignorando arquivo não suportado: {file_name}")

    # Determinar o diretório de destino
    if matches:
        # Se houver matches, usar o primeiro domínio como nome da pasta
        destination_dir = os.path.join(base_destination_dir,
                                       current_month_year, matches[0])
    else:
        # Se não houver matches, usar a pasta "others"
        image_date = os.path.normpath(file_name).split(os.sep)[1]
        destination_dir = os.path.join(base_destination_dir,
                                       current_month_year,
                                       "others", image_date)

    # Criar o diretório de destino (se não existir)
    create_directory(destination_dir)

    # Gerar um nome de arquivo único baseado no índice

    # Extrair a extensão do arquivo original
    name_file = os.path.split(file_name)[-1]
    new_file_path = os.path.join(destination_dir, name_file)

    # Mover o arquivo para o diretório de destino
    shutil.copy2(file_name, new_file_path)
    os.remove(file_name)  # Remove o arquivo original

    log.info(f"Arquivo movido para: {new_file_path}")


def main():
    # Obter o mês e ano atual no formato MM-YYYY
    current_month_year = datetime.now().strftime("%m-%Y")

    # Percorrer todos os diretórios e arquivos dentro de base_media_dir
    for root, dirs, files in tqdm(os.walk(base_media_dir)):
        for file_name in tqdm(files):
            file_path = os.path.join(root, file_name)

            # Verificar se o arquivo é uma imagem ou vídeo
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp',
                                           '.gif')):
                # É uma imagem
                image = cv2.imread(file_path)
                matches = process_image(image)
            elif file_name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                # É um vídeo, capturar o primeiro quadro
                image = get_first_frame(file_path)
                matches = process_image(image)
            else:
                # Ignorar arquivos que não são imagens ou vídeos
                print(f"Ignorando arquivo não suportado: {file_name}")
                continue

            # Determinar o diretório de destino
            if matches:
                # Se houver matches, usar o primeiro domínio como nome da pasta
                destination_dir = os.path.join(base_destination_dir,
                                               current_month_year, matches[0])
            else:
                # Se não houver matches, usar a pasta "others"
                destination_dir = os.path.join(base_destination_dir,
                                               current_month_year,
                                               "others" + "\\" +
                                               root.split("\\")[-1])

            # Criar o diretório de destino (se não existir)
            create_directory(destination_dir)

            # Gerar um nome de arquivo único baseado no índice

            # Extrair a extensão do arquivo original
            new_file_path = os.path.join(destination_dir, file_name)

            # Mover o arquivo para o diretório de destino
            shutil.copy2(file_name, new_file_path)
            os.remove(file_name)  # Remove o arquivo original

            log.info(f"Arquivo movido para: {new_file_path}")


# Diretório base onde as mídias estão armazenadas
base_media_dir = env["FIRST_DONWLOAD_FOLDER"]

# Diretório base para onde as mídias serão movidas
base_destination_dir = env["DESTINATION_DIR_IMAGE"]

# Executa o script
if __name__ == "__main__":
    main()
