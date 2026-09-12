from __future__ import annotations

import pathlib
from datetime import timedelta
from typing import Any, Literal

import pydantic
from pydantic_merge import BaseModel

# region SSL


class SSLConfig(BaseModel):
    cafile: pathlib.Path | None = None
    capath: pathlib.Path | None = None
    cadata: str | bytes | None = None

    @property
    def cafile_normalized(self) -> pathlib.Path | None:
        if self.cafile is not None:
            return self.cafile

        return None

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
    read: timedelta | Literal[False] | None = None
    write: timedelta | Literal[False] | None = None
    connect: timedelta | Literal[False] | None = None
    pool: timedelta | Literal[False] | None = None

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
    log_path: pathlib.Path | None = pydantic.Field(
        default=None, description="Path to the log directory", examples=["/var/log/http_config", "./logs"]
    )

    def with_sub_log_path(self, sub_path: str | pathlib.Path) -> HTTPConfig:
        if self.log_path is None:
            return self

        return self.model_copy(
            update={"log_path": self.log_path / sub_path},
        )
