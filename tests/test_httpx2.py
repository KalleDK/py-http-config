import asyncio
import json
from datetime import timedelta
from pathlib import Path

import pytest

try:
    import httpx2
except ModuleNotFoundError as error:
    if error.name == "httpx2":
        pytest.skip("httpx2 is not installed", allow_module_level=True)
    raise

from http_config import HTTPConfig, LimitConfig, TimeoutConfig
from http_config.httpx2.client import (
    create_async_client,
    create_async_transport,
    create_limits,
    create_sync_client,
    create_sync_transport,
    create_timeout,
    create_transport_dct,
)
from http_config.httpx2.logger import AsyncTransportLogger, FileLogger, SyncTransportLogger


def test_create_timeout_handles_all_supported_values() -> None:
    assert create_timeout(None) is None
    assert create_timeout(False) == httpx2.Timeout(timeout=None)
    assert create_timeout(timedelta(seconds=3)) == httpx2.Timeout(timeout=3)
    assert create_timeout(TimeoutConfig()) is None

    timeout = create_timeout(
        TimeoutConfig(
            timeout=timedelta(seconds=1),
            read_timeout=False,
            write_timeout=timedelta(seconds=2),
            connect_timeout=timedelta(seconds=3),
        )
    )

    assert timeout is not None
    assert timeout.connect == 3
    assert timeout.read is None
    assert timeout.write == 2
    assert timeout.pool == 1


def test_create_limits_preserves_configured_values() -> None:
    assert create_limits(None) is None

    limits = create_limits(LimitConfig(max_connections=10, max_keepalive_connections=4))

    assert limits is not None
    assert limits.max_connections == 10
    assert limits.max_keepalive_connections == 4


def test_create_transport_dict_includes_proxy_limits_and_ssl() -> None:
    transport = create_transport_dct(
        HTTPConfig(
            proxy="https://proxy.example",
            limits=LimitConfig(max_connections=8, max_keepalive_connections=3),
        )
    )

    proxy = transport.get("proxy")
    limits = transport.get("limits")
    assert proxy == "https://proxy.example"
    assert limits is not None
    assert limits.max_connections == 8
    assert limits.max_keepalive_connections == 3
    assert transport["verify"].check_hostname is True


def test_create_transport_dict_uses_defaults() -> None:
    transport = create_transport_dct(None)

    assert transport["verify"].check_hostname is True


def test_create_transports_wrap_logging_enabled_transports(tmp_path: Path) -> None:
    async_transport = create_async_transport(HTTPConfig(log_path=tmp_path / "async"))
    sync_transport = create_sync_transport(HTTPConfig(log_path=tmp_path / "sync"))

    assert isinstance(async_transport, AsyncTransportLogger)
    assert isinstance(sync_transport, SyncTransportLogger)
    assert (tmp_path / "async").is_dir()
    assert (tmp_path / "sync").is_dir()
    asyncio.run(async_transport.aclose())
    sync_transport.close()


def test_create_sync_client_applies_timeout_auth_and_middleware() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"url": str(request.url)}, request=request)

    def middleware(_: httpx2.BaseTransport) -> httpx2.BaseTransport:
        return httpx2.MockTransport(handler)

    config = HTTPConfig(timeout=TimeoutConfig(timeout=timedelta(seconds=4)))
    auth = httpx2.BasicAuth("user", "password")

    with create_sync_client(config, middleware=middleware, auth=auth) as client:
        response = client.get("https://example.test/resource")

        assert response.status_code == 200
        assert client.timeout == httpx2.Timeout(timeout=4)
        assert client.auth is auth


def test_create_async_client_applies_callable_auth_and_middleware() -> None:
    async def scenario() -> None:
        def handler(request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(200, request=request)

        def middleware(_: httpx2.AsyncBaseTransport) -> httpx2.AsyncBaseTransport:
            return httpx2.MockTransport(handler)

        auth = httpx2.DigestAuth("user", "password")

        def create_auth(_: httpx2.AsyncClient) -> httpx2.Auth:
            return auth

        async with create_async_client(middleware=middleware, auth=create_auth) as client:
            response = await client.get("https://example.test/resource")

            assert response.status_code == 200
            assert client.auth is auth

    asyncio.run(scenario())


def test_create_clients_support_default_config_and_auth_objects() -> None:
    async def close_async_client() -> None:
        auth = httpx2.BasicAuth("user", "password")
        client = create_async_client(auth=auth)
        assert client.auth is auth
        await client.aclose()

    def create_auth(_: httpx2.Client) -> httpx2.Auth:
        return auth

    auth = httpx2.BasicAuth("user", "password")
    client = create_sync_client(auth=auth)
    assert client.auth is auth
    client.close()

    callable_client = create_sync_client(auth=create_auth)
    assert callable_client.auth is auth
    callable_client.close()
    asyncio.run(close_async_client())


def test_file_logger_rejects_existing_file_and_disabled_directory_creation(tmp_path: Path) -> None:
    file_path = tmp_path / "log"
    file_path.write_text("")
    with pytest.raises(RuntimeError, match="not a directory"):
        FileLogger(file_path)

    missing_path = tmp_path / "missing"
    with pytest.raises(RuntimeError, match="does not exists"):
        FileLogger(missing_path, create_dir=False)


def test_sync_transport_logger_writes_request_and_response(tmp_path: Path) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(201, content=b"response", request=request)

    logger = SyncTransportLogger(httpx2.MockTransport(handler), tmp_path)
    request = httpx2.Request("POST", "https://example.test", content=b"request")
    response = logger.handle_request(request)

    assert response.status_code == 201
    assert len(list(tmp_path.glob("*_REQ_HEADERS.json"))) == 1
    assert len(list(tmp_path.glob("*_RES_HEADERS.json"))) == 1
    assert next(iter(tmp_path.glob("*_REQ_BODY.txt"))).read_bytes() == b"request"
    assert next(iter(tmp_path.glob("*_RES_BODY.txt"))).read_bytes() == b"response"

    headers_path = next(iter(tmp_path.glob("*_REQ_HEADERS.json")))
    assert json.loads(headers_path.read_text())["method"] == "POST"


def test_sync_transport_logger_skips_empty_bodies(tmp_path: Path) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(204, request=request)

    logger = SyncTransportLogger(httpx2.MockTransport(handler), tmp_path)
    logger.handle_request(httpx2.Request("GET", "https://example.test"))

    assert list(tmp_path.glob("*_REQ_BODY.txt")) == []
    assert list(tmp_path.glob("*_RES_BODY.txt")) == []


def test_async_transport_logger_writes_request_and_response(tmp_path: Path) -> None:
    async def scenario() -> None:
        async def handler(request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(202, content=b"async response", request=request)

        logger = AsyncTransportLogger(httpx2.MockTransport(handler), tmp_path)
        request = httpx2.Request("GET", "https://example.test", content=b"async request")
        response = await logger.handle_async_request(request)

        assert response.status_code == 202

    asyncio.run(scenario())
    assert next(iter(tmp_path.glob("*_REQ_BODY.txt"))).read_bytes() == b"async request"
    assert next(iter(tmp_path.glob("*_RES_BODY.txt"))).read_bytes() == b"async response"
