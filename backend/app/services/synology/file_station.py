from typing import Optional
from app.services.synology.client import SynologyClient
from app.services.synology.exceptions import SynologyApiError


class FileStation:
    """
    FileStation API client for Synology NAS.
    Provides methods for browsing and searching files on the NAS.
    """

    API_PATH = "entry.cgi"

    def __init__(self, client: SynologyClient = None):
        self.client = client or SynologyClient()

    def _request(self, api: str, method: str, version: int, data: dict = None) -> dict:
        """
        Make authenticated request to FileStation API.
        
        Args:
            api: API name (e.g., "SYNO.FileStation.List")
            method: Method name (e.g., "list")
            version: API version
            data: Additional parameters
            
        Returns:
            API response dict
        """
        params = {
            "api": api,
            "method": method,
            "version": version,
        }
        if data:
            params.update(data)
        return self.client.post(self.API_PATH, data=params)

    def list_shares(self) -> dict:
        """
        List all shared folders (volumes) on the NAS.
        
        Returns:
            Dict with 'shares' list containing {name, path, isdir} entries
        """
        return self._request("SYNO.FileStation.List", "list_share", 1)

    def list_folders(
        self,
        folder_path: str = "/",
        offset: int = 0,
        limit: int = 100,
        sort_by: str = "name",
        sort_direction: str = "ASC",
    ) -> dict:
        """
        List folders and files in a directory.
        
        Args:
            folder_path: Path to directory (e.g., "/chat")
            offset: Pagination offset
            limit: Max results per page
            sort_by: Sort field (name, size, mtime)
            sort_direction: ASC or DESC
            
        Returns:
            Dict with 'files' list containing file info
        """
        return self._request(
            "SYNO.FileStation.List",
            "list",
            2,
            {
                "folder_path": folder_path,
                "offset": offset,
                "limit": limit,
                "sort_by": sort_by,
                "sort_direction": sort_direction,
            },
        )

    def list_files(
        self,
        folder_path: str = "/",
        offset: int = 0,
        limit: int = 100,
        sort_by: str = "name",
        sort_direction: str = "ASC",
        pattern: str = None,
        filetype: str = None,
    ) -> dict:
        """
        List files (not directories) in a directory.
        
        Args:
            folder_path: Path to directory
            pattern: Glob pattern to filter files (e.g., "*.pdf")
            filetype: "file" or "dir" to filter type
            
        Returns:
            Dict with 'files' list
        """
        data = {
            "folder_path": folder_path,
            "offset": offset,
            "limit": limit,
            "sort_by": sort_by,
            "sort_direction": sort_direction,
        }
        if pattern:
            data["pattern"] = pattern
        if filetype:
            data["filetype"] = filetype
        return self._request("SYNO.FileStation.List", "list", 2, data)

    def get_info(self) -> dict:
        """Get FileStation version and capabilities."""
        return self._request("SYNO.FileStation.Info", "getinfo", 2)

    def get_file_info(self, path: str) -> dict:
        """
        Get detailed info for a specific file or folder.
        
        Args:
            path: Full path to file/folder
        """
        return self._request(
            "SYNO.FileStation.List",
            "getinfo",
            2,
            {"path": path},
        )

    def search(
        self,
        folder_path: str = "/",
        keyword: str = None,
        filetype: str = "file",
        limit: int = 100,
    ) -> dict:
        """
        Search for files by name pattern.
        
        Args:
            folder_path: Directory to search in
            keyword: Search string (supports wildcards)
            filetype: "file" or "dir"
            limit: Max results
            
        Returns:
            Dict with matching files
        """
        return self._request(
            "SYNO.FileStation.Search",
            "list",
            3,
            {
                "folder_path": folder_path,
                "keyword": keyword or "",
                "filetype": filetype,
                "limit": limit,
            },
        )