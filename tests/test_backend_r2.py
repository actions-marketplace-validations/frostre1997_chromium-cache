import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import backends.r2 as r2mod  # noqa: E402
from backends.base import BackendContext  # noqa: E402
from backends.r2 import R2Backend  # noqa: E402


def _ctx(tmp_path, config=None, version="131.0.6778.85"):
    work = tmp_path / "work"
    return BackendContext(
        version=version,
        workdir=work,
        src_path=work / "src",
        config=config or {},
        exclude=[],
        shallow=True,
    )


@pytest.fixture(autouse=True)
def clean_r2_env():
    prefixes = ("CLOUDFLARE_", "R2_", "CF_", "RCLONE_CONFIG_R2_")
    saved = {k: v for k, v in os.environ.items() if k.startswith(prefixes)}
    for k in saved:
        del os.environ[k]
    yield
    for k in list(os.environ):
        if k.startswith(prefixes):
            del os.environ[k]
    os.environ.update(saved)


def test_missing_account_id():
    with pytest.raises(SystemExit):
        r2mod._configure_rclone({"bucket": "b"})


def test_missing_access_key():
    with pytest.raises(SystemExit):
        r2mod._configure_rclone({"account_id": "abc", "bucket": "b"})


def test_missing_secret():
    with pytest.raises(SystemExit):
        r2mod._configure_rclone({
            "account_id": "abc",
            "access_key_id": "key",
            "bucket": "b",
        })


def test_configure_from_config():
    r2mod._configure_rclone({
        "account_id": "abc123",
        "access_key_id": "AK",
        "secret_access_key": "SK",
    })
    assert os.environ["RCLONE_CONFIG_R2_TYPE"] == "s3"
    assert os.environ["RCLONE_CONFIG_R2_PROVIDER"] == "Cloudflare"
    assert os.environ["RCLONE_CONFIG_R2_ACCESS_KEY_ID"] == "AK"
    assert os.environ["RCLONE_CONFIG_R2_SECRET_ACCESS_KEY"] == "SK"
    assert os.environ["RCLONE_CONFIG_R2_ENDPOINT"] == "https://abc123.r2.cloudflarestorage.com"
    assert os.environ["RCLONE_CONFIG_R2_ACL"] == "private"


def test_configure_from_env(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "envacc")
    monkeypatch.setenv("CLOUDFLARE_R2_ACCESS_KEY_ID", "envAK")
    monkeypatch.setenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "envSK")
    r2mod._configure_rclone({})
    assert os.environ["RCLONE_CONFIG_R2_ACCESS_KEY_ID"] == "envAK"
    assert "envacc.r2.cloudflarestorage.com" in os.environ["RCLONE_CONFIG_R2_ENDPOINT"]


def test_config_overrides_env(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "envacc")
    monkeypatch.setenv("CLOUDFLARE_R2_ACCESS_KEY_ID", "envAK")
    monkeypatch.setenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "envSK")
    r2mod._configure_rclone({
        "account_id": "cfgacc",
        "access_key_id": "cfgAK",
        "secret_access_key": "cfgSK",
    })
    assert os.environ["RCLONE_CONFIG_R2_ACCESS_KEY_ID"] == "cfgAK"
    assert "cfgacc.r2.cloudflarestorage.com" in os.environ["RCLONE_CONFIG_R2_ENDPOINT"]


def test_r2_config_default_path():
    c = r2mod._r2_config({"bucket": "my-bucket"})
    assert c["remote"] == "r2"
    assert c["path"] == "my-bucket/chromium"
    assert "--s3-no-check-bucket" in c["extra_args"]
    assert "--transfers" in c["extra_args"]
    assert "32" in c["extra_args"]


def test_r2_config_custom_prefix():
    c = r2mod._r2_config({"bucket": "b", "prefix": "custom/dir"})
    assert c["path"] == "b/custom/dir"


def test_r2_config_no_prefix():
    c = r2mod._r2_config({"bucket": "b", "prefix": ""})
    assert c["path"] == "b"


def test_r2_config_extra_args_passthrough():
    c = r2mod._r2_config({"bucket": "b", "extra_args": ["--log-level", "DEBUG"]})
    assert c["extra_args"][-2:] == ["--log-level", "DEBUG"]


def test_r2_config_missing_bucket():
    with pytest.raises(SystemExit):
        r2mod._r2_config({})


def test_restore_delegates(tmp_path):
    ctx = _ctx(tmp_path, config={
        "account_id": "a", "access_key_id": "k", "secret_access_key": "s", "bucket": "b",
    })
    with patch.object(r2mod.RcloneBackend, "restore", return_value=True) as m:
        assert R2Backend().restore(ctx) is True
    m.assert_called_once()
    passed_ctx = m.call_args.args[0]
    assert passed_ctx.config["remote"] == "r2"
    assert passed_ctx.config["path"].startswith("b/")


def test_save_delegates(tmp_path):
    ctx = _ctx(tmp_path, config={
        "account_id": "a", "access_key_id": "k", "secret_access_key": "s", "bucket": "b",
    })
    with patch.object(r2mod.RcloneBackend, "save") as m:
        R2Backend().save(ctx)
    m.assert_called_once()


def test_probe_delegates(tmp_path):
    ctx = _ctx(tmp_path, config={
        "account_id": "a", "access_key_id": "k", "secret_access_key": "s", "bucket": "b",
    })
    with patch.object(r2mod.RcloneBackend, "probe", return_value=42.5) as m:
        assert R2Backend().probe(ctx) == 42.5
    m.assert_called_once()
