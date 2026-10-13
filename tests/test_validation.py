import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from lxml import etree

from agaas_saft.validation import NS, capabilities, validate_saft

FIXTURES = Path(__file__).parent / "fixtures"


def example(version="1.40"):
    return (FIXTURES / f"upstream-{version}.xml").read_bytes()


def changed(path, value, *, version="1.40"):
    tree = etree.fromstring(example(version))
    tree.find(path, NS).text = value
    return etree.tostring(tree)


@pytest.mark.parametrize("version", ["1.30", "1.40"])
def test_official_examples_validate_against_the_selected_schema(version):
    result = validate_saft(example(version), schema_version=version)
    assert result.status == "valid"
    assert result.checks == {"xml": "passed", "schema": "passed", "code_lists": "not_requested"}


def test_version_selection_cannot_silently_accept_an_old_header():
    result = validate_saft(example("1.30"))
    assert result.status == "invalid"
    assert "SAFT_VERSION_MISMATCH" in [issue.code for issue in result.issues]


def test_140_accepts_high_precision_currency_amount_that_130_rejects():
    tree = etree.fromstring(example("1.30"))
    debit = tree.find(".//s:DebitAmount", NS)
    etree.SubElement(debit, f"{{{NS['s']}}}CurrencyCode").text = "EUR"
    currency = etree.SubElement(debit, f"{{{NS['s']}}}CurrencyAmount")
    currency.text = "10.00"
    assert validate_saft(etree.tostring(tree), schema_version="1.30").status == "valid"
    amount = "12345678901234567890.123456789012345678"
    currency.text = amount
    older = validate_saft(etree.tostring(tree), schema_version="1.30")
    assert older.status == "invalid"
    assert older.issues[0].code == "XSD_VALIDATION"
    tree.find("s:Header/s:AuditFileVersion", NS).text = "1.40"
    assert validate_saft(etree.tostring(tree)).status == "valid"


def test_required_field_is_enforced_by_xsd_and_has_a_location():
    tree = etree.fromstring(example())
    element = tree.find("s:Header/s:SoftwareID", NS)
    element.getparent().remove(element)
    result = validate_saft(etree.tostring(tree))
    assert result.checks["schema"] == "failed"
    assert result.issues[0].code == "XSD_VALIDATION"
    assert result.issues[0].line > 0
    assert result.issues[0].path


@pytest.mark.parametrize("xml", [b"", b"<AuditFile>", b"\xff\x00", b"<a/><a/>"])
def test_malformed_xml_is_invalid(xml):
    result = validate_saft(xml)
    assert result.status == "invalid"
    assert result.issues[0].code == "XML_SYNTAX"


def test_wrong_namespace_is_rejected():
    assert validate_saft(b"<AuditFile/>").issues[0].code == "SAFT_ROOT"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_entity_declarations_are_rejected_without_reading_local_files(tmp_path, encoding):
    secret = tmp_path / "private.txt"
    secret.write_text("DO_NOT_DISCLOSE")
    xml = (
        f'<?xml version="1.0" encoding="{encoding}"?>'
        f'<!DOCTYPE AuditFile [<!ENTITY file SYSTEM "{secret.as_uri()}">]>'
        '<AuditFile xmlns="urn:StandardAuditFile-Taxation-Financial:NO">&file;</AuditFile>'
    ).encode(encoding)
    result = validate_saft(xml)
    assert result.status == "invalid"
    assert result.issues[0].code == "XML_DOCTYPE"
    assert "DO_NOT_DISCLOSE" not in json.dumps(result.to_dict())


def test_external_schema_location_is_ignored():
    xml = example().replace(
        b"Norwegian_SAF-T_Financial_Schema_v_1.40.xsd", b"http://127.0.0.1:9/unavailable.xsd"
    )
    assert validate_saft(xml).status == "valid"


def test_no_file_values_in_schema_diagnostics():
    xml = changed("s:Header/s:AuditFileDateCreated", "CUSTOMER_SECRET")
    report = validate_saft(xml)
    assert report.status == "invalid"
    assert "CUSTOMER_SECRET" not in json.dumps(report.to_dict())


def test_unknown_configuration_is_an_error():
    assert validate_saft(example(), schema_version="2.0").exit_code == 2
    result = validate_saft(example(), codelist_year=2027)
    assert result.exit_code == 2
    assert result.issues[0].code == "UNSUPPORTED_CODELIST_YEAR"


@pytest.mark.parametrize("year", [2025, 2026])
def test_official_example_has_known_business_and_tax_codes(year):
    result = validate_saft(example(), codelist_year=year)
    assert result.status == "valid"
    assert result.checks["code_lists"] == "passed"


@pytest.mark.parametrize(
    ("path", "value", "code"),
    [
        (".//s:GroupingCode", "999999", "GROUPING_CODE_UNKNOWN"),
        (".//s:GroupingCategory", "wrong-category", "GROUPING_CODE_UNKNOWN"),
        (".//s:StandardTaxCode", "01", "TAX_CODE_UNKNOWN"),
    ],
)
def test_schema_valid_but_unlisted_codes_fail_only_the_requested_code_check(path, value, code):
    xml = changed(path, value)
    assert validate_saft(xml).status == "valid"
    result = validate_saft(xml, codelist_year=2026)
    assert result.checks["schema"] == "passed"
    assert result.checks["code_lists"] == "failed"
    assert result.issues[0].code == code


def test_official_na_exceptions_are_accepted_as_membership_only():
    tree = etree.fromstring(example())
    for path in (".//s:GroupingCategory", ".//s:GroupingCode", ".//s:StandardTaxCode"):
        tree.find(path, NS).text = "NA"
    assert validate_saft(etree.tostring(tree), codelist_year=2026).status == "valid"


def test_parallel_validations_do_not_share_error_logs():
    inputs = [example(), changed("s:Header/s:AuditFileDateCreated", "wrong")] * 10
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(validate_saft, inputs))
    assert [result.status for result in results] == ["valid", "invalid"] * 10
    assert all(not result.issues for result in results[::2])


def test_repeated_problems_are_capped_and_not_reported_as_success():
    tree = etree.fromstring(example())
    accounts = tree.find("s:MasterFiles/s:GeneralLedgerAccounts", NS)
    account = etree.tostring(accounts[0]).replace(b"</AccountID>", b"bad</AccountID>")
    accounts.clear()
    for _ in range(120):
        node = etree.fromstring(account)
        node.find("s:GroupingCode", NS).text = "999999"
        accounts.append(node)
    report = validate_saft(etree.tostring(tree), codelist_year=2026)
    assert report.exit_code == 1
    assert len(report.issues) == 100
    assert report.truncated


def test_bundled_sources_and_examples_match_the_upstream_manifest():
    root = Path(__file__).parents[1]
    manifest = json.loads((root / "src/agaas_saft/data/provenance.json").read_text())
    for source in manifest["files"]:
        assert hashlib.sha256((root / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    assert capabilities()["upstream_commit"] == manifest["commit"]
