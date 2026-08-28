# HTTP Config

Shared, typed configuration for Python HTTP clients. Keep proxy, timeout, connection-limit, TLS, and request
logging settings in one Pydantic model and reuse them across client integrations.

The core configuration models are client-library independent. The project currently provides an integration
for [HTTPX](https://www.python-httpx.org/), with support for additional HTTP libraries planned for the future.

## Installation

Using `uv`:

```console
uv add "http-config[httpx]"
```

Using `pip`:

```console
python -m pip install "http-config[httpx]"
```

The `httpx` extra installs the current HTTPX integration. The configuration models are available without any
client-library extra, allowing future integrations to be added independently.

## Quick Start

```python
from datetime import timedelta

from http_config import HTTPConfig, LimitConfig, TimeoutConfig
from http_config.httpx import sync_client


config = HTTPConfig(
    timeout=TimeoutConfig(
        timeout=timedelta(seconds=10),
        connect_timeout=timedelta(seconds=3),
    ),
    limits=LimitConfig(
        max_connections=50,
        max_keepalive_connections=10,
    ),
)

with sync_client(config) as client:
    response = client.get("https://httpbin.org/get")
    response.raise_for_status()
    print(response.json())
```

For asynchronous code, use `async_client`:

```python
from http_config.httpx import async_client


async def fetch() -> dict:
    async with async_client() as client:
        response = await client.get("https://httpbin.org/get")
        response.raise_for_status()
        return response.json()
```

## Configuration

`HTTPConfig` supports these settings:

| Setting | Type | Description |
| --- | --- | --- |
| `proxy` | `str \| None` | Proxy URL passed to the active client integration. |
| `timeout` | `timedelta \| False \| TimeoutConfig \| None` | Overall or per-operation timeout. `False` disables the timeout. |
| `limits` | `LimitConfig \| None` | Maximum open and keep-alive connections. |
| `ssl` | `bool \| SSLConfig \| None` | TLS verification mode and custom certificate sources. |
| `log_path` | `Path \| None` | Directory where request and response files are recorded by supported integrations. |

### Merging Configuration

The configuration models use [`pydantic-merge`](https://github.com/tylerjamesyoung/pydantic-merge). Use
`model_merge()` to create a validated copy with updates applied recursively. Nested configuration is merged
instead of replaced, so an update to one timeout value preserves the other timeout values:

```python
from datetime import timedelta

from http_config import HTTPConfig, TimeoutConfig


base = HTTPConfig(
    timeout=TimeoutConfig(
        timeout=timedelta(seconds=10),
        read_timeout=timedelta(seconds=5),
    ),
)
updated = base.model_merge(
    HTTPConfig(
        timeout=TimeoutConfig(connect_timeout=timedelta(seconds=3)),
    )
)

assert updated.timeout.timeout == timedelta(seconds=10)
assert updated.timeout.read_timeout == timedelta(seconds=5)
assert updated.timeout.connect_timeout == timedelta(seconds=3)
```

### TLS

The default is normal certificate verification. Set `ssl=False` to disable verification, or provide a
custom CA file, directory, or certificate data with `SSLConfig`:

If [certifi](https://github.com/certifi/python-certifi) is installed, its CA bundle is used automatically
when no explicit `cafile` is configured. Install it separately with `uv add certifi` or
`python -m pip install certifi`. An explicit `cafile` takes precedence; set `ignore_certifi=True` to opt out
of the automatic certifi fallback.

```python
from pathlib import Path

from http_config import HTTPConfig, SSLConfig


config = HTTPConfig(
    ssl=SSLConfig(
        cafile=Path("certificates/ca.pem"),
    ),
)
```

To disable the automatic certifi fallback:

```python
from http_config import HTTPConfig, SSLConfig


config = HTTPConfig(ssl=SSLConfig(ignore_certifi=True))
```

`SSLConfig.create()` is useful when settings come from optional application configuration:

```python
ssl_setting = SSLConfig.create(insecure=False, cafile=Path("ca.pem"))
```

### Request Logging

Set `log_path` to enable file-based transport logging. The directory is created automatically. Each request
gets JSON header files and body files when a body is present, paired by a timestamp-based prefix and request
index.

```python
from pathlib import Path

from http_config import HTTPConfig
from http_config.httpx import sync_client


config = HTTPConfig(log_path=Path("http-logs"))
with sync_client(config) as client:
    client.get("https://httpbin.org/get")
```

## HTTPX Middleware and Authentication

The current HTTPX client factories accept an optional transport middleware function and either an HTTPX auth
object or a factory that receives the client:

```python
import httpx

from http_config.httpx import sync_client


def middleware(transport: httpx.BaseTransport) -> httpx.BaseTransport:
    return transport


with sync_client(
    middleware=middleware,
    auth=httpx.BasicAuth("user", "password"),
) as client:
    response = client.get("https://example.com")
```

## Development

Install the test dependencies and run the suite with:

```console
uv sync --group test
uv run pytest
uv run ruff check
```

## License

This project is available under the [MIT License](LICENSE).
