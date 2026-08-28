import pathlib
import tomllib

from http_config import __version__


def test_version_project() -> None:
    with pathlib.Path("pyproject.toml").open("rb") as fp:
        config = tomllib.load(fp)
    assert __version__ == config["project"]["version"]


def test_version_bump() -> None:
    with pathlib.Path(".bumpversion.toml").open("rb") as fp:
        config = tomllib.load(fp)

    assert __version__ == config["tool"]["bumpversion"]["current_version"]
