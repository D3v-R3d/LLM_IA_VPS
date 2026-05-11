"""
SynologyService - Central service layer for Synology NAS operations.

All NAS operations go through this service. It manages:
- Authentication lifecycle (login cached per instance)
- Client session management
- Business logic (search, list, find operations)

Tools must NOT instantiate SynologyClient directly.
"""

from typing import Optional
from functools import lru_cache

from app.services.synology import SynologyClient, SynologyAuth, FileStation
from app.services.synology.exceptions import SynologyApiError, SynologyConnectionError


class SynologyService:
    """
    Central service for Synology NAS operations.

    Manages authenticated session internally. Single instance provides
    cached authentication across all tool calls.
    """

    _instance: Optional["SynologyService"] = None

    def __init__(self):
        self._client: Optional[SynologyClient] = None
        self._auth: Optional[SynologyAuth] = None
        self._logged_in: bool = False

    @classmethod
    def get_instance(cls) -> "SynologyService":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing or re-authentication)."""
        cls._instance = None

    def _ensure_authenticated(self) -> None:
        """Ensure we have an authenticated session."""
        if self._logged_in:
            return

        self._client = SynologyClient()
        self._auth = SynologyAuth(self._client)
        self._auth.login()
        self._logged_in = True

    def _get_file_station(self) -> FileStation:
        """Get authenticated FileStation instance."""
        self._ensure_authenticated()
        return FileStation(self._client)

    def list_shares(self) -> dict:
        """
        List all shared folders (volumes) on the NAS.

        Returns:
            Dict with 'shares' list containing {name, path, isdir} entries
        """
        fs = self._get_file_station()
        return fs.list_shares()

    def list_folder(self, folder_path: str = "/") -> dict:
        """
        List contents of a directory.

        Args:
            folder_path: Path to directory. Defaults to "/".

        Returns:
            Dict with 'files' list containing file info
        """
        fs = self._get_file_station()
        return fs.list_folders(folder_path=folder_path)

    def search(
        self,
        keyword: str,
        folder_path: Optional[str] = None,
        recursive: bool = True,
        filetype: str = "file",
        limit: int = 100,
    ) -> dict:
        """
        Search for files/directories by keyword.

        Args:
            keyword: Search string to match against filenames
            folder_path: Directory to search in. If None, searches globally from "/".
            recursive: Search subfolders recursively. Defaults to True.
            filetype: "file" or "dir" filter. Defaults to "file".
            limit: Maximum number of results. Defaults to 100.

        Returns:
            Dict with matching files/directories
        """
        fs = self._get_file_station()
        search_path = folder_path if folder_path else "/"
        return fs.search(
            folder_path=search_path,
            keyword=keyword,
            recursive=recursive,
            filetype=filetype,
            limit=limit,
        )

    def find_file(self, name: str, folder_path: Optional[str] = None) -> dict:
        """
        Find a file by exact or partial name match.

        Args:
            name: Filename or partial name to search for
            folder_path: Optional folder to scope search. If None, searches globally.

        Returns:
            Dict with matching files
        """
        return self.search(keyword=name, folder_path=folder_path, recursive=True, filetype="file")

    def find_folder(self, name: str, folder_path: Optional[str] = None) -> dict:
        """
        Find a directory by exact or partial name match.

        Args:
            name: Folder name or partial name to search for
            folder_path: Optional folder to scope search. If None, searches globally.

        Returns:
            Dict with matching directories
        """
        return self.search(keyword=name, folder_path=folder_path, recursive=True, filetype="dir")

    def get_file_info(self, path: str) -> dict:
        """
        Get detailed info for a specific file or folder.

        Args:
            path: Full path to file/folder

        Returns:
            Dict with file/folder metadata
        """
        fs = self._get_file_station()
        return fs.get_file_info(path=path)
