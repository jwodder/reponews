from os.path import expanduser
from pathlib import Path
from typing import Any
import pytest
from ghissues.config import Configuration
from ghissues.util import get_default_state_file
from testlib import filecases


@pytest.mark.parametrize("tomlfile,expected", filecases("config", "*.toml"))
def test_parse_config(tmp_home: Path, tomlfile: Path, expected: Any) -> None:
    (tmp_home / ".github").touch()
    config = Configuration.from_toml_file(tomlfile)
    if expected["state_file"] is None:
        expected["state_file"] = get_default_state_file()
    for key in ("auth_token_file", "state_file"):
        if expected[key] is not None:
            expected[key] = expanduser(expected[key])
    assert config.for_json() == expected
