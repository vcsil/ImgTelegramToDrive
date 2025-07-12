#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb  8 13:58:16 2025.

Telegram Media Downloader

Downloads media from a specified Telegram group and organizes it by date.
@author: vcsil
"""

from pyrogram.errors import FloodWait
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import dotenv_values
from typing import Optional
from pathlib import Path
import nest_asyncio
import asyncio

from driveSync.uploaded_filesdirs import UploadedFilesDirs
from driveSync.drive_client import DriveClient
from driveSync.drive_auth import DriveAuth
from utils.logger_setup import SetupLogger
from organizeGroups import organize_midia
from utils.utils import BUILD_ABSPATH
from mainDrive import sync_upload

# Apply patch to allow multiple event loops
nest_asyncio.apply()


class TelegramMediaDownloader:
    """A class to download media from Telegram groups."""

    def __init__(self):
        """Initialize the downloader with configuration from env var."""
        # Load environment variables
        env = dotenv_values()

        # Configure paths
        self.base_dir = Path(__file__).parent.parent
        self.download_folder = self.base_dir / env["FIRST_DONWLOAD_FOLDER"]
        self.credentials_dir = self.base_dir / "credentials"
        self.logs_dir = self.base_dir / "logs"

        # Ensure directories exist
        self.download_folder.mkdir(parents=True, exist_ok=True)
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Configure logging
        self.log = SetupLogger(self.logs_dir / "log-main.txt", "main")

        # Telegram API credentials
        self.api_id = env["TELEGRAM_API_ID"]
        self.api_hash = env["TELEGRAM_API_HASH"]
        self.phone_number = env["TELEGRAM_PHONE_NUMBER"]
        self.group_id = int(env["TELEGRAM_GROUP_ID"], 0)

        # Initialize Pyrogram client
        self.app = Client(
            "minha_conta",
            api_id=self.api_id,
            api_hash=self.api_hash,
            phone_number=self.phone_number,
            workdir=str(self.credentials_dir)
        )

        # Set up message handler
        @self.app.on_message(filters.chat(self.group_id) &
                             (filters.photo | filters.video))
        async def handle_new_message(client, message):
            """Handle new messages with media."""
            self.log.info(f"Nova mensagem recebida: {message.id}")
            await self.process_media(message)

    async def process_media(self, message: Message) -> None:
        """
        Process and download media from a message.

        Args
        ----
            message: The Telegram message containing media
        """
        try:
            if not message.media:
                return

            # Get message date and format as YYYY-MM-DD
            message_date = message.date
            date_folder = message_date.strftime("%Y-%m-%d")

            # Create directory for this date
            media_folder = self.download_folder / date_folder
            media_folder.mkdir(exist_ok=True)

            # Determine file extension based on media type
            file_extension = self._get_file_extension(message)

            # Formata o horário da mensagem e cria o novo nome do arquivo
            message_time = message_date.strftime("%H-%M")
            new_file_name = f"{message_time} - {message.id}{file_extension}"

            # Define full file path
            file_path = media_folder / new_file_name

            # Download the media
            self.log.info(f"Baixando mídia da mensagem {message.id}...")
            await self.app.download_media(message, file_name=str(file_path))
            self.log.info(
                f"Mídia {message.id} baixada com sucesso em {media_folder}!")

            # Process images and videos with organize_midia
            if message.photo or message.video:
                new_file_path = organize_midia(str(file_path), message.date,
                                               self.log)
                sync_upload(new_file_path, self.log, drive_client, local_dir,
                            obj_uploads,  envv["GDRIVE_BASE_FOLDER_ID"])

        except Exception as e:
            self.log.error(
                f"Erro ao processar a mensagem {message.id}: {e}")

    def _get_file_extension(self, message: Message) -> str:
        """
        Determine the appropriate file extension based on media type.

        Args
        ----
            message: The Telegram message containing media

        Returns
        -------
            str: The file extension with leading dot
        """
        if message.photo:
            return ".jpg"
        elif message.video:
            return ".mp4"
        else:
            return ".dat"  # Default extension

    async def download_historical_media(self, min_id: int,
                                        max_id: Optional[int] = None) -> None:
        """
        Download media from historical messages in the specified group.

        Args
        ----
            min_id: Minimum message ID to download
            max_id: Maximum message ID to download (if None, no upper limit)
        """
        try:
            self.log.info("Conectado à conta do Telegram!")
            group = await self.app.get_chat(self.group_id)
            self.log.info(f"Acessando o grupo: {group.title}")

            async for message in self.app.get_chat_history(group.id):
                try:
                    # Check if message ID is within specified range
                    if message.id < min_id:
                        self.log.info(
                            f"Atingido o ID mínimo {min_id}. Parando.")
                        break

                    if max_id and message.id > max_id:
                        continue

                    if message.photo or message.video:
                        await self.process_media(message)

                except Exception as e:
                    self.log.error(
                        f"Erro ao processar a mensagem {message.id}: {e}")
                    # Add small delay before continuing
                    await asyncio.sleep(1)

        except FloodWait as e:
            wait_time = e.value
            self.log.warning(
                f"FloodWait detectado. Esperando {wait_time}s para continuar.")
            await asyncio.sleep(wait_time)
            # Try processing again after waiting
            await self.download_historical_media(min_id, message.id-1)

    async def list_groups(self) -> dict:
        """
        List all available groups/chats with their IDs.

        Returns
        -------
            dict: Mapping of group names to their IDs
        """
        groups = {}
        async with self.app:
            async for dialog in self.app.get_dialogs():
                if dialog.chat.title:
                    groups[dialog.chat.title] = dialog.chat.id
                    self.log.info(
                        f"Nome: {dialog.chat.title} | ID: {dialog.chat.id}")

        return groups

    async def run(self, download_historical: bool = False, min_id: int = 0,
                  max_id: Optional[int] = None) -> None:
        """
        Run the media downloader.

        Args
        ----
            download_historical: Whether to download historical media
            min_id: Minimum message ID for historical download
            max_id: Maximum message ID for historical download
        """
        # Start the client
        await self.app.start()
        self.log.info("Cliente iniciado.")

        try:
            # Download historical media if requested
            if download_historical:
                self.log.info(
                    f"Baixando (IDs {min_id} até {max_id or 'atual'})...")
                await self.download_historical_media(min_id, max_id)
                self.log.info("Download histórico concluído.")

            # Keep the client running for new messages
            self.log.info("Aguardando novas mensagens...")
            # An alternative to idle() that's more explicit
            await asyncio.Event().wait()

        except KeyboardInterrupt:
            self.log.info("Interrupção de teclado detectada. Encerrando...")

        except Exception as e:
            self.log.error(f"Erro durante a execução: {e}")

        finally:
            # Stop the client
            await self.app.stop()
            obj_uploads.update_dict()
            self.log.info("Cliente encerrado.")


async def main():
    """Entry point for the script."""
    # Create the downloader instance
    downloader = TelegramMediaDownloader()

    # Uncomment any of these lines as needed:

    # To list available groups
# =============================================================================
#     groups = await downloader.list_groups()
#     print("Grupos disponíveis:", groups)
# =============================================================================

    # To download historical media
# =============================================================================
#     await downloader.run(download_historical=True, min_id=61027,
#                          max_id=61890)
# =============================================================================

    # To just listen for new media
    await downloader.run()


if __name__ == "__main__":
    # Inicia conexao e autenticacao com o drive
    client_secrets_path = BUILD_ABSPATH(
        __file__, "../credentials/client_secrets.json")
    auth = DriveAuth(client_secrets_path).authenticate()

    # Inicia cliente do drive
    drive_client = DriveClient(auth)

    # Lê arquivo que armazena informações do que já foi sincronizado
    obj_uploads = UploadedFilesDirs(BUILD_ABSPATH(__file__, "../uploads.json"))

    envv = dotenv_values()
    local_dir = BUILD_ABSPATH(__file__, "..", envv["DESTINATION_DIR_IMAGE"])

    asyncio.run(main())
