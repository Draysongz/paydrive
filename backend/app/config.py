from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Paths
    inbox_path: str = str(Path(__file__).parent.parent.parent / "inbox")
    database_url: str = "sqlite+aiosqlite:///./paydrive.db"

    # AI Provider: claude | openai | groq | ollama
    ai_provider: str = "claude"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llava"

    # Approval thresholds
    auto_approve_limit: float = 250.00
    approval_timeout_hours: int = 24

    # PayPal
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"

    # Web3
    web3_rpc_url: str = "http://localhost:8545"
    web3_private_key: str = ""
    web3_chain_id: int = 84532  # Base Sepolia default
    escrow_mode: str = "simple"  # simple | multisig
    simple_vault_address: str = ""
    multisig_vault_address: str = ""
    multisig_threshold: int = 2
    gas_limit_cap: int = 500000

    # Webhook notifications
    webhook_url: str = ""
    email_notifications_enabled: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    model_config = {
        "env_file": [".env", str(Path(__file__).parent.parent.parent / ".env")],
        "env_file_encoding": "utf-8",
    }


settings = Settings()
