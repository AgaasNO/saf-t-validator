"""Validate bytes without network access, file resolution or application dependencies."""

import csv
import io
import json
from functools import lru_cache
from importlib.resources import files

from lxml import etree

from .report import Report

MAX_INPUT_BYTES = 64 * 1024 * 1024
NAMESPACE = "urn:StandardAuditFile-Taxation-Financial:NO"
NS = {"s": NAMESPACE}
SCHEMA_VERSIONS = ("1.30", "1.40")
CODELIST_YEARS = (2025, 2026)


def _data(name):
    return files("agaas_saft").joinpath("data", name)


def _parser():
    return etree.XMLParser(
        resolve_entities=False, load_dtd=False, no_network=True, huge_tree=False, recover=False
    )


@lru_cache
def _schema_bytes(version):
    return _data(f"financial-{version}.xsd").read_bytes()


@lru_cache
def _codes():
    grouping = csv.DictReader(
        io.StringIO(_data("grouping-2025-2026.csv").read_text(encoding="utf-8-sig")),
        delimiter=";",
    )
    tax = csv.DictReader(
        io.StringIO(_data("tax-codes.csv").read_text(encoding="utf-8-sig")), delimiter=";"
    )
    return (
        frozenset((row["GroupingCategory"], row["GroupingCode"]) for row in grouping),
        frozenset(row["Code"] for row in tax),
    )


def _text(element, path):
    return element.findtext(path, default="", namespaces=NS)


def validate_saft(
    xml: bytes, *, schema_version: str = "1.40", codelist_year: int | None = None
) -> Report:
    """Check an explicit XSD and, optionally, the selected business/VAT code lists.

    Does not validate journal arithmetic, completeness or NS 4102 account semantics.
    Unsupported requested checks return an error, never a passing partial result.
    """
    report = Report(
        "saft",
        checks={"xml": "not_run", "schema": "not_run", "code_lists": "not_requested"},
        metadata={"schema_version": schema_version, "codelist_year": codelist_year},
    )
    if schema_version not in SCHEMA_VERSIONS:
        report.add("UNSUPPORTED_SCHEMA", "Supported schemas: 1.30, 1.40.", error=True)
        return report
    if codelist_year is not None and codelist_year not in CODELIST_YEARS:
        report.add("UNSUPPORTED_CODELIST_YEAR", "Bundled code-list years: 2025, 2026.", error=True)
        return report
    if codelist_year is not None:
        report.checks["code_lists"] = "not_run"
    if len(xml) > MAX_INPUT_BYTES:
        report.add("INPUT_TOO_LARGE", "The test interface accepts at most 64 MiB.", error=True)
        return report
    try:
        root = etree.fromstring(xml, parser=_parser())
    except (etree.XMLSyntaxError, ValueError) as exc:
        report.checks["xml"] = "failed"
        line = exc.position[0] if isinstance(exc, etree.XMLSyntaxError) else None
        report.add("XML_SYNTAX", "Input is not a well-formed XML document.", line=line)
        return report
    tree = root.getroottree()
    if tree.docinfo.doctype:
        report.checks["xml"] = "failed"
        report.add("XML_DOCTYPE", "DTD and entity declarations are not accepted.")
        return report
    report.checks["xml"] = "passed"
    if root.tag != f"{{{NAMESPACE}}}AuditFile":
        report.checks["schema"] = "failed"
        report.add("SAFT_ROOT", "Expected SAF-T Financial AuditFile and its Norwegian namespace.")
        return report

    # Keep the schema object per invocation: lxml's error log belongs to that object.
    schema = etree.XMLSchema(etree.fromstring(_schema_bytes(schema_version), parser=_parser()))
    report.checks["schema"] = "passed"
    if not schema.validate(tree):
        report.checks["schema"] = "failed"
        for issue in schema.error_log:
            # libxml messages can contain accounting values. Return locations and rule names only.
            report.add(
                "XSD_VALIDATION",
                f"XML violates the selected schema ({issue.type_name}).",
                line=issue.line,
                path=issue.path,
            )
    if _text(root, "s:Header/s:AuditFileVersion") != schema_version:
        report.checks["schema"] = "failed"
        report.add(
            "SAFT_VERSION_MISMATCH", "AuditFileVersion must equal the requested schema version."
        )
    if report.status != "valid" or codelist_year is None:
        return report

    grouping, tax = _codes()
    report.checks["code_lists"] = "passed"
    for account in root.findall("s:MasterFiles/s:GeneralLedgerAccounts/s:Account", NS):
        pair = (_text(account, "s:GroupingCategory"), _text(account, "s:GroupingCode"))
        # An explicit NA exception needs accounting review, beyond this membership check.
        if pair != ("NA", "NA") and pair not in grouping:
            report.add(
                "GROUPING_CODE_UNKNOWN",
                "GroupingCategory and GroupingCode are not a listed business-statement pair.",
                line=account.sourceline,
                path=tree.getpath(account),
            )
    for code in root.findall("s:MasterFiles/s:TaxTable/s:TaxTableEntry/s:TaxCodeDetails", NS):
        if _text(code, "s:StandardTaxCode") not in tax | {"NA"}:
            report.add(
                "TAX_CODE_UNKNOWN",
                "StandardTaxCode is not in the Norwegian standard VAT code list.",
                line=code.sourceline,
                path=tree.getpath(code),
            )
    if report.status != "valid":
        report.checks["code_lists"] = "failed"
    return report


def capabilities() -> dict:
    """Describe available checks, including their provenance, without reading customer files."""
    provenance = json.loads(_data("provenance.json").read_text())
    return {
        "interface_version": 1,
        "schema_versions": list(SCHEMA_VERSIONS),
        "codelist_years": list(CODELIST_YEARS),
        "codelist_scope": "business-statement-and-standard-vat",
        "ns4102": "caller-supplied-catalogue-membership-only",
        "max_input_bytes": MAX_INPUT_BYTES,
        "upstream_commit": provenance["commit"],
    }
