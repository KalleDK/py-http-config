from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict

import httpx2

from http_config._ssl import create_ssl_context
from http_config.config import HTTPConfig, LimitConfig, TimeoutConfig
from http_config.httpx2.logger import AsyncTransportLogger, SyncTransportLogger

if TYPE_CHECKING:
    import ssl
    from collections.abc import Callable

__version__ = "0.1.0"


# region Timeout


class TimeoutDict(TypedDict):
    timeout: NotRequired[float | None]
    read: NotRequired[float | None]
    write: NotRequired[float | None]
    connect: NotRequired[float | None]
    pool: NotRequired[float | None]


def create_timeout(value: timedelta | Literal[False] | TimeoutConfig | None) -> httpx2.Timeout | None:
    match value:
        case None:
            return None
        case TimeoutConfig() as v:
            if v.timeout is None and v.read is None and v.write is None and v.connect is None:
                return None

            timeout_dct: TimeoutDict = {
                "timeout": None,
            }
            if v.timeout is not None and v.timeout is not False:
                timeout_dct["timeout"] = v.timeout.total_seconds()
            if v.read is not None:
                timeout_dct["read"] = None if v.read is False else v.read.total_seconds()
            if v.write is not None:
                timeout_dct["write"] = None if v.write is False else v.write.total_seconds()
            if v.connect is not None:
                timeout_dct["connect"] = None if v.connect is False else v.connect.total_seconds()
            if v.pool is not None:
                timeout_dct["pool"] = None if v.pool is False else v.pool.total_seconds()
            return httpx2.Timeout(**timeout_dct)
        case timedelta():
            return httpx2.Timeout(timeout=value.total_seconds())
        case False:
            return httpx2.Timeout(timeout=None)


# endregion

# region Limits


def create_limits(value: LimitConfig | None) -> httpx2.Limits | None:
    if value is None:
        return None
    return httpx2.Limits(
        max_connections=value.max_connections,
        max_keepalive_connections=value.max_keepalive_connections,
    )


# endregion

# region Transport


class TransportDict(TypedDict):
    verify: ssl.SSLContext
    proxy: NotRequired[str]
    limits: NotRequired[httpx2.Limits]


def create_transport_dct(http_config: HTTPConfig | None) -> TransportDict:
    if http_config is None:
        http_config = HTTPConfig()

    transport_dct: TransportDict = {
        "verify": create_ssl_context(http_config.ssl),
    }

    if (proxy := http_config.proxy) is not None:
        transport_dct["proxy"] = proxy

    if (limits := create_limits(http_config.limits)) is not None:
        transport_dct["limits"] = limits

    return transport_dct


def create_async_transport(
    http_config: HTTPConfig | None = None,
    middleware: Callable[[httpx2.AsyncBaseTransport], httpx2.AsyncBaseTransport] | None = None,
) -> httpx2.AsyncBaseTransport:

    transport = httpx2.AsyncHTTPTransport(**create_transport_dct(http_config))
    if http_config is not None and http_config.log_path is not None:
        transport = AsyncTransportLogger(transport, http_config.log_path)
    if middleware is not None:
        transport = middleware(transport)
    return transport


def create_sync_transport(
    http_config: HTTPConfig | None = None,
    middleware: Callable[[httpx2.BaseTransport], httpx2.BaseTransport] | None = None,
) -> httpx2.BaseTransport:

    transport = httpx2.HTTPTransport(**create_transport_dct(http_config))
    if http_config is not None and http_config.log_path is not None:
        transport = SyncTransportLogger(transport, http_config.log_path)
    if middleware is not None:
        transport = middleware(transport)

    return transport


# endregion

# region Client


class ClientDict(TypedDict):
    timeout: NotRequired[httpx2.Timeout]


def _create_client_dict(config: HTTPConfig) -> ClientDict:
    dct: ClientDict = {}
    if (timeout := create_timeout(config.timeout)) is not None:
        dct["timeout"] = timeout
    return dct


def create_async_client(
    http_config: HTTPConfig | None = None,
    middleware: Callable[[httpx2.AsyncBaseTransport], httpx2.AsyncBaseTransport] | None = None,
    auth: Callable[[httpx2.AsyncClient], httpx2.Auth] | httpx2.Auth | None = None,
) -> httpx2.AsyncClient:

    if http_config is None:
        http_config = HTTPConfig()

    client_dct = _create_client_dict(http_config)

    client = httpx2.AsyncClient(**client_dct, transport=create_async_transport(http_config, middleware=middleware))

    if isinstance(auth, httpx2.Auth):
        client.auth = auth
    elif auth is not None:
        client.auth = auth(client)
    return client


def create_sync_client(
    http_config: HTTPConfig | None = None,
    middleware: Callable[[httpx2.BaseTransport], httpx2.BaseTransport] | None = None,
    auth: Callable[[httpx2.Client], httpx2.Auth] | httpx2.Auth | None = None,
) -> httpx2.Client:

    if http_config is None:
        http_config = HTTPConfig()

    client_dct = _create_client_dict(http_config)

    client = httpx2.Client(**client_dct, transport=create_sync_transport(http_config, middleware=middleware))

    if isinstance(auth, httpx2.Auth):
        client.auth = auth
    elif auth is not None:
        client.auth = auth(client)
    return client


# endregion
