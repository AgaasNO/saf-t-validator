"""Exercise the built archive from outside the checkout, with source imports excluded."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

root = Path(__file__).resolve().parents[1]
(wheel,) = (root / "dist").glob("*.whl")
with ZipFile(wheel) as archive:
    names = archive.namelist()
    assert not any(name.startswith(("tests/", "docs/", ".git/")) for name in names)
    assert len([name for name in names if name.endswith(".xsd")]) == 2
    assert len([name for name in names if name.endswith(".csv")]) == 2
    assert "agaas_saft/UPSTREAM-README.md" in names
    assert "agaas_saft/NOTICE.md" in names
    assert wheel.stat().st_size < 150_000

code = """
import json, sys
sys.path.insert(0, sys.argv[1])
import agaas_saft
assert sys.argv[1] in agaas_saft.__file__
from agaas_saft.validation import validate_saft
report = validate_saft(sys.stdin.buffer.read(), schema_version=sys.argv[2])
print(json.dumps(report.to_dict()))
raise SystemExit(report.exit_code)
"""
with tempfile.TemporaryDirectory() as temporary:
    for version in ("1.30", "1.40"):
        fixture = (root / f"tests/fixtures/upstream-{version}.xml").read_bytes()
        response = subprocess.run(
            [sys.executable, "-I", "-c", code, str(wheel), version],
            input=fixture,
            capture_output=True,
            cwd=temporary,
            check=True,
        )
        assert json.loads(response.stdout)["status"] == "valid"
print(f"Verified both schemas from {wheel.name}: {wheel.stat().st_size} bytes")
