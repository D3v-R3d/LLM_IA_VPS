from pydantic_settings import BaseSettings
import os


def _read_secret_file(filepath: str) -> str | None:
    if filepath and os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    return None


class SynologySettings(BaseSettings):
    host: str
    port: int = 5001
    username: str = ""
    password: str = ""
    protocol: str = "https"
    timeout: int = 30

    @property
    def base_url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"

    class Config:
        env_prefix = "SYNOLOGY_"

    def __init__(self, **kwargs):
        username_file = os.environ.get("SYNOLOGY_USERNAME_FILE", "")
        password_file = os.environ.get("SYNOLOGY_PASSWORD_FILE", "")
        if not kwargs.get("username") and username_file:
            kwargs["username"] = _read_secret_file(username_file) or ""
        if not kwargs.get("password") and password_file:
            kwargs["password"] = _read_secret_file(password_file) or ""
        super().__init__(**kwargs)


synology_settings = SynologySettings()