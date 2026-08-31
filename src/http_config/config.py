from __future__ import annotations

import pathlib
from datetime import timedelta
from typing import Any, Literal

import pydantic
from pydantic_merge import BaseModel

# region SSL


def load_certifi() -> pathlib.Path | None:
    try:
        import certifi

        return pathlib.Path(certifi.where())
    except ImportError:
        return None


CERTIFI_PATH: pathlib.Path | None = load_certifi()


class SSLConfig(BaseModel):
    cafile: pathlib.Path | None = None
    capath: pathlib.Path | None = None
    cadata: str | bytes | None = None
    ignore_certifi: bool | None = None

    @property
    def cafile_normalized(self) -> pathlib.Path | None:
        if self.cafile is not None:
            return self.cafile

        if self.ignore_certifi is True:
            return None

        return CERTIFI_PATH

    @classmethod
    def create(
        cls,
        insecure: bool | None = None,
        cafile: pathlib.Path | None = None,
        capath: pathlib.Path | None = None,
        cadata: str | bytes | None = None,
    ) -> SSLConfig | bool | None:
        if insecure is True:
            return False

        if cafile is None and capath is None and cadata is None:
            if insecure is None:
                return None
            return True

        return cls(cafile=cafile, capath=capath, cadata=cadata)


# endregion


# region Timeout


class TimeoutConfig(BaseModel):
    timeout: timedelta | Literal[False] | None = None
    read_timeout: timedelta | Literal[False] | None = None
    write_timeout: timedelta | Literal[False] | None = None
    connect_timeout: timedelta | Literal[False] | None = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def _validate_base(cls, v: timedelta | str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(v, (timedelta, str)):
            return {"timeout": v}
        return v


# endregion

# region Limits


class LimitConfig(BaseModel):
    max_connections: int | None = None
    max_keepalive_connections: int | None = None


# endregion


class HTTPConfig(BaseModel):
    proxy: str | None = None
    timeout: timedelta | Literal[False] | TimeoutConfig | None = None
    limits: LimitConfig | None = None
    ssl: bool | SSLConfig | None = None
    log_path: pathlib.Path | None = None

    def with_sub_log_path(self, sub_path: str | pathlib.Path) -> HTTPConfig:
        if self.log_path is None:
            return self

        return self.model_copy(
            update={"log_path": self.log_path / sub_path},
        )
