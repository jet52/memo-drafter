import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str = ""
    courtlistener_api_key: str = ""

    # Model settings
    claude_model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.3
    max_tokens: int = 8192

    # Verification settings
    enable_verification: bool = True
    verification_cache_dir: str = "./cache"
    court_data: str = ""  # Path to local court data directory (markdown/ and pdfs/ subdirs)

    # Output settings
    include_appendix: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def __init__(self, **kwargs):
        # Ensure dotenv values are in os.environ before pydantic reads them
        super().__init__(**kwargs)
        # Fall back to os.environ if pydantic didn't find it
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
