def test_fail_when_short(tmp_path, capsys):
    with patch("disk_guard.measure",
               return_value=_fake_info(str(tmp_path), 5.0, 200.0)):
        with pytest.raises(SystemExit) as ei:
            disk_guard.check(30, str(tmp_path), probe_only=False)
    assert ei.value.code == 1
    err = capsys.readouterr().err
    assert "insufficient disk" in err
    assert "need >= 30 GB" in err
    assert "have 5.00 GB" in err           # was "have 5.0 GB"
    assert "cleanser" in err
    assert "min-free-gb: 0" in err


def test_fail_when_target_exceeds_total(tmp_path, capsys):
    with patch("disk_guard.measure",
               return_value=_fake_info(str(tmp_path), 50.0, 84.0)):
        with pytest.raises(SystemExit) as ei:
            disk_guard.check(200, str(tmp_path), probe_only=False)
    assert ei.value.code == 1
    err = capsys.readouterr().err
    assert "exceeds total volume size" in err
    assert "84.00 GB" in err               # was "84.0 GB"
