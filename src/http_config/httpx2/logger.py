from __future__ import annotations

import contextlib
import dataclasses
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

import httpx2

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Generator
    from zoneinfo import ZoneInfo


# region Logger

TZ: ZoneInfo | None = None


def now() -> datetime:
    return datetime.now(TZ)


@dataclasses.dataclass
class FileSession:
    log_dir: pathlib.Path
    prefix: str
    suffix: str
    idx: int

    def _write_req_headers(self, request: httpx2.Request) -> None:
        data = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
        }
        self.log_dir.joinpath(f"{self.prefix}_{self.idx:04d}_REQ_HEADERS.json").write_text(json.dumps(data, indent=2))

    def _write_req_body(self, data: bytes) -> None:
        if not data:
            return
        self.log_dir.joinpath(f"{self.prefix}_{self.idx:04d}_REQ_BODY{self.suffix}").write_bytes(data)

    def _write_res_headers(self, response: httpx2.Response) -> None:
        data = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
        }
        self.log_dir.joinpath(f"{self.prefix}_{self.idx:04d}_RES_HEADERS.json").write_text(json.dumps(data, indent=2))

    def _write_res_body(self, data: bytes) -> None:
        if not data:
            return
        self.log_dir.joinpath(f"{self.prefix}_{self.idx:04d}_RES_BODY{self.suffix}").write_bytes(data)

    async def awrite_request(self, request: httpx2.Request) -> None:
        self._write_req_headers(request)
        self._write_req_body(await request.aread())

    async def awrite_response(self, response: httpx2.Response) -> None:
        self._write_res_headers(response)
        self._write_res_body(await response.aread())

    def write_request(self, request: httpx2.Request) -> None:
        self._write_req_headers(request)
        self._write_req_body(request.read())

    def write_response(self, response: httpx2.Response) -> None:
        self._write_res_headers(response)
        self._write_res_body(response.read())


class FileLogger:
    def __init__(self, log_dir: pathlib.Path, suffix: str = ".txt", create_dir: bool = True) -> None:
        if not log_dir.is_dir():
            if log_dir.exists():
                raise RuntimeError("log_dir is not a directory")
            if not create_dir:
                raise RuntimeError("log_dir does not exists")
            log_dir.mkdir(parents=True)

        self.log_dir = log_dir
        self.prefix = now().strftime("%Y%m%d_%H%M%S")
        self.suffix = suffix
        self._idx = 0

    def get_idx(self) -> int:
        idx = self._idx
        self._idx += 1
        return idx

    @contextlib.contextmanager
    def session(self) -> Generator[FileSession, Any]:
        yield FileSession(self.log_dir, self.prefix, self.suffix, self.get_idx())


class AsyncTransportLogger(httpx2.AsyncBaseTransport):
    def __init__(self, transport: httpx2.AsyncBaseTransport, log_dir: pathlib.Path, suffix: str = ".txt") -> None:
        self._logger = FileLogger(log_dir, suffix=suffix)
        self.transport = transport

    async def handle_async_request(
        self,
        request: httpx2.Request,
    ) -> httpx2.Response:
        with self._logger.session() as session:
            await session.awrite_request(request)
            response = await self.transport.handle_async_request(request)
            await session.awrite_response(response)
            return response


class SyncTransportLogger(httpx2.BaseTransport):
    def __init__(self, transport: httpx2.BaseTransport, log_dir: pathlib.Path, suffix: str = ".txt") -> None:
        self._logger = FileLogger(log_dir, suffix=suffix)
        self.transport = transport

    def handle_request(
        self,
        request: httpx2.Request,
    ) -> httpx2.Response:
        with self._logger.session() as session:
            session.write_request(request)
            response = self.transport.handle_request(request)
            session.write_response(response)
            return response


# endregion
