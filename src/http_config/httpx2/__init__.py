from http_config.httpx2.client import create_async_client as async_client
from http_config.httpx2.client import create_sync_client as sync_client

__all__ = [
    "async_client",
    "sync_client",
]
