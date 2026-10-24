import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import version as version_mod  # noqa: E402


def test_is_valid_ok():
    assert version_mod.is_valid("131.0.6778.85")
    assert version_mod.is_valid("1.2.3.4")


def test_is_valid_bad():
    assert not version_mod.is_valid("131.0.6778")
    assert not version_mod.is_valid("v131.0.6778.85")
    assert not version_mod.is_valid("")
    assert not version_mod.is_valid("abc")


def _mock_urlopen(payload: bytes):
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=MagicMock(read=lambda: payload))
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def test_resolve_passthrough():
    assert version_mod.resolve("131.0.6778.85") == "131.0.6778.85"


def test_resolve_invalid():
    with pytest.raises(SystemExit):
        version_mod.resolve("not-a-version")


def test_get_latest_stable_ok():
    body = json.dumps([{"version": "131.0.6778.85"}]).encode()
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
        assert version_mod.get_latest_stable() == "131.0.6778.85"


def test_get_latest_stable_empty():
    body = json.dumps([]).encode()
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
        with pytest.raises(SystemExit):
            version_mod.get_latest_stable()


def test_get_latest_stable_network_error():
    with patch("urllib.request.urlopen", side_effect=Exception("no net")):
        with pytest.raises(SystemExit):
            version_mod.get_latest_stable()


def test_resolve_empty_fetches():
    body = json.dumps([{"version": "132.0.6900.10"}]).encode()
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(body)):
        assert version_mod.resolve("") == "132.0.6900.10"
