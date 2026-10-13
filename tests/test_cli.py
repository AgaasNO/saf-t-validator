import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def run(*args, data=None, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "agaas_saft.cli", *args],
        input=data,
        capture_output=True,
        cwd=cwd,
        timeout=20,
        check=False,
    )


def test_info_describes_supported_versions_and_missing_2027_codes():
    response = run("info")
    assert response.returncode == 0
    info = json.loads(response.stdout)
    assert info["schema_versions"] == ["1.30", "1.40"]
    assert 2027 not in info["codelist_years"]


def test_stdin_returns_one_json_result_and_no_diagnostics_on_stderr():
    response = run("validate", "-", data=(FIXTURES / "upstream-1.40.xml").read_bytes())
    report = json.loads(response.stdout)
    assert response.returncode == 0
    assert report["interface_version"] == 1
    assert report["status"] == "valid"
    assert response.stderr == b""


def test_paths_with_spaces_and_other_working_directory(tmp_path):
    fixture = tmp_path / "test æøå.xml"
    fixture.write_bytes((FIXTURES / "upstream-1.40.xml").read_bytes())
    response = run("validate", str(fixture), cwd=tmp_path)
    assert response.returncode == 0
    assert json.loads(response.stdout)["status"] == "valid"


@pytest.mark.parametrize(
    ("args", "data", "status", "code"),
    [
        (["validate", "-"], b"broken", 1, "XML_SYNTAX"),
        (["validate", "/definitely-missing/file.xml"], None, 2, "INPUT_IO"),
        (["validate", "-", "--schema-version", "2.0"], b"", 2, "UNSUPPORTED_SCHEMA"),
        (["validate", "-", "--codelist-year", "2027"], b"", 2, "UNSUPPORTED_CODELIST_YEAR"),
        (["validate", "-", "--codelist-year", "wrong"], b"", 2, "USAGE"),
        (["accounts", "-"], b"{}", 2, "USAGE"),
        (["accounts", "-", "--catalogue", "-"], b"{}", 2, "USAGE"),
    ],
)
def test_failures_have_distinct_exit_codes_and_a_json_report(args, data, status, code):
    response = run(*args, data=data)
    assert response.returncode == status
    assert json.loads(response.stdout)["issues"][0]["code"] == code
    assert response.stderr == b""


def test_oversized_input_fails_before_parsing(tmp_path):
    path = tmp_path / "large.xml"
    with path.open("wb") as stream:
        stream.truncate(64 * 1024 * 1024 + 1)
    response = run("validate", str(path))
    assert response.returncode == 2
    assert json.loads(response.stdout)["issues"][0]["code"] == "INPUT_TOO_LARGE"


def test_accounts_command_uses_a_supplied_file(tmp_path):
    catalogue = tmp_path / "catalogue.json"
    catalogue.write_text(
        json.dumps({"standard": "NS 4102:2023", "source": "synthetic", "accounts": ["10000"]})
    )
    mappings = json.dumps(
        {
            "standard": "NS 4102:2023",
            "mappings": [{"account_id": "local", "standard_account": "10000"}],
        }
    ).encode()
    response = run("accounts", "-", "--catalogue", str(catalogue), data=mappings)
    assert response.returncode == 0
    assert json.loads(response.stdout)["checks"]["mappings"] == "passed"
