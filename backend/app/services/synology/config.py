from pydantic_settings import BaseSettings


class SynologySettings(BaseSettings):
    host: str
    port: int = 5001
    username: str
    password: str
    protocol: str = "https"
    timeout: int = 30

    @property
    def base_url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"

    class Config:
        env_prefix = "SYNOLOGY_"


synology_settings = SynologySettings()