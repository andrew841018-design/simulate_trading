from pydantic_settings import BaseSettings, SettingsConfigDict


class AccountSettings(BaseSettings):
    DATABASE_URL: str ## variable inside .env file
    TEST_DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=".env")
account_settings = AccountSettings()