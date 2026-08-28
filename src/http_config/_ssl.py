from __future__ import annotations

import ssl as _ssl

from http_config.config import CERTIFI_PATH, SSLConfig

# region SSL


def create_insecure_ssl_context() -> _ssl.SSLContext:
    ctx = _ssl.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE
    return ctx


def create_ssl_context(ssl_config: SSLConfig | bool | None) -> _ssl.SSLContext:
    match ssl_config:
        case None:
            return _ssl.create_default_context()
        case SSLConfig() as _ssl_config:
            return _ssl.create_default_context(
                cafile=_ssl_config.cafile_normalized,
                capath=_ssl_config.capath,
                cadata=_ssl_config.cadata,
            )

        case bool():
            if ssl_config is False:
                return create_insecure_ssl_context()
            return _ssl.create_default_context(
                cafile=CERTIFI_PATH,
            )


# endregion
