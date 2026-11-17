from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_PORT: int = 8000
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "k8s-realm"
    KEYCLOAK_ADMIN_USER: str = "admin"
    KEYCLOAK_ADMIN_PASSWORD: str = "adminpassword"
    OIDC_USERNAME_PREFIX: str = "oidc:"
    KUBECONFIG_PATH: str = ""

    class Config:
        env_file = "../.env"
        extra = "ignore"

settings = Settings()
