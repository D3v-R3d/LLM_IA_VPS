import httpx
from app.services.synology.config import synology_settings
from app.services.synology.exceptions import SynologyConnectionError


class SynologyClient:
    """
    HTTP client for Synology NAS API communication.
    Maintains a persistent session with cookie storage for authentication.
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        protocol: str = None,
        timeout: int = None,
        verify_ssl: bool = False,
    ):
        self.host = host or synology_settings.host
        self.port = port or synology_settings.port
        self.protocol = protocol or synology_settings.protocol
        self.timeout = timeout or synology_settings.timeout
        self.verify_ssl = verify_ssl
        self.base_url = f"{self.protocol}://{self.host}:{self.port}"
        self.sid = None
        self._session = None

    def _get_session(self) -> httpx.Client:
        """Get or create persistent HTTP session with cookie support."""
        if self._session is None:
            self._session = httpx.Client(timeout=self.timeout, verify=self.verify_ssl)
        return self._session

    def _build_url(self, path: str) -> str:
        """Build full API URL from relative path."""
        return f"{self.base_url}/webapi/{path}"

    def request(
        self,
        method: str,
        path: str,
        params: dict = None,
        data: dict = None,
        json: dict = None,
    ) -> dict:
        """
        Make HTTP request to Synology API.
        Returns JSON response or error dict if HTML error page received.
        """
        url = self._build_url(path)
        try:
            session = self._get_session()
            response = session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
            )
            if response.text.startswith('<!DOCTYPE'):
                return {'error': {'code': 103}, 'success': False}
            return response.json()
        except httpx.ConnectError as e:
            raise SynologyConnectionError(f"Cannot connect to {self.base_url}: {e}")
        except httpx.TimeoutException:
            raise SynologyConnectionError(f"Connection timeout to {self.base_url}")
        except httpx.HTTPStatusError as e:
            raise SynologyConnectionError(f"HTTP error {e.response.status_code}")

    def get(self, path: str, params: dict = None) -> dict:
        """Make GET request."""
        return self.request("GET", path, params=params)

    def post(self, path: str, params: dict = None, data: dict = None, json: dict = None) -> dict:
        """Make POST request."""
        return self.request("POST", path, params=params, data=data, json=json)

    def set_sid(self, sid: str):
        """Store session ID from authentication."""
        self.sid = sid

    def clear_session(self):
        """Close session and clear SID."""
        self.sid = None
        if self._session:
            self._session.close()
            self._session = None

    def close(self):
        """Alias for clear_session()."""
        self.clear_session()