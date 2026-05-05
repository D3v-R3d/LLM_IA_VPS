from app.services.synology.client import SynologyClient
from app.services.synology.config import synology_settings
from app.services.synology.exceptions import SynologyAuthError


class SynologyAuth:
    """
    Authentication manager for Synology NAS.
    Handles login/logout via SYNO.API.Auth API.
    """

    AUTH_API = "auth.cgi"

    def __init__(self, client: SynologyClient = None):
        self.client = client or SynologyClient()

    def login(self, username: str = None, password: str = None, session: str = "FileStation") -> str:
        """
        Authenticate with Synology NAS.
        
        Args:
            username: NAS username (defaults to config)
            password: NAS password (defaults to config)
            session: Session name (default: FileStation)
            
        Returns:
            Session ID (SID)
            
        Raises:
            SynologyAuthError: If login fails
        """
        username = username or synology_settings.username
        password = password or synology_settings.password

        params = {
            "api": "SYNO.API.Auth",
            "method": "login",
            "version": "3",
            "account": username,
            "passwd": password,
            "session": session,
            "format": "cookie",
        }

        result = self.client.post(self.AUTH_API, data=params)

        if result.get("success"):
            token = result["data"]["sid"]
            self.client.set_sid(token)
            return token

        raise SynologyAuthError(f"Login failed: {result.get('error', {})}")

    def logout(self) -> bool:
        """End the current session."""
        params = {
            "api": "SYNO.API.Auth",
            "method": "logout",
            "version": "3",
            "session": "FileStation",
        }

        result = self.client.post(self.AUTH_API, data=params)

        if result.get("success"):
            self.client.clear_session()
            return True

        return False

    def check(self) -> bool:
        """Check if current session is valid."""
        if not self.client.sid:
            return False

        params = {
            "api": "SYNO.API.Auth",
            "method": "check",
            "version": "1",
        }

        result = self.client.post(self.AUTH_API, data=params)
        return result.get("success", False)