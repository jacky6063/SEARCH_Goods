"""Quick connectivity test against Supabase chat tables."""

import os

from dotenv import load_dotenv
from supabase import Client, create_client


def require_env(var_name: str) -> str:
    """Fetch env var or exit with clear message."""
    value = os.getenv(var_name)
    if not value:
        raise SystemExit(f"Missing environment variable: {var_name}")
    return value


def main() -> None:
    load_dotenv()

    url = require_env("SUPABASE_URL")
    anon_key = require_env("SUPABASE_KEY")

    client: Client = create_client(url, anon_key)
    response = client.table("chat_messages").select("*").limit(5).execute()
    print(response.data or [])


if __name__ == "__main__":
    main()
