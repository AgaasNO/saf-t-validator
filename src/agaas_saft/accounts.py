"""Membership checks against a separately supplied, licensed NS 4102 catalogue."""

import hashlib
import json
import re

from .report import Report
from .validation import MAX_INPUT_BYTES

STANDARD = "NS 4102:2023"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _document(data):
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("Document is too large")
    value = json.loads(data, object_pairs_hook=_unique_object)
    if not isinstance(value, dict) or value.get("standard") != STANDARD:
        raise ValueError("Expected NS 4102:2023 document")
    return value


def validate_accounts(mappings: bytes, *, catalogue: bytes) -> Report:
    """Require each local account to map once to an exact code in the supplied catalogue.

    The caller supplies the complete set of accounts to check. No licensed standard is bundled;
    a passing result does not establish that the catalogue or the accounting choices are correct.
    """
    report = Report(
        "accounts",
        checks={"catalogue": "not_run", "mappings": "not_run"},
        metadata={"standard": STANDARD, "catalogue_sha256": hashlib.sha256(catalogue).hexdigest()},
    )
    try:
        reference = _document(catalogue)
        codes = reference.get("accounts")
        if (
            not isinstance(reference.get("source"), str)
            or not reference["source"].strip()
            or not isinstance(codes, list)
            or not codes
            or any(
                not isinstance(code, str) or not re.fullmatch(r"[1-8][0-9]{3,4}", code)
                for code in codes
            )
            or len(set(codes)) != len(codes)
        ):
            raise ValueError("Invalid catalogue")
    except (ValueError, UnicodeError, RecursionError):
        report.checks["catalogue"] = "failed"
        report.add(
            "CATALOGUE_INVALID", "Supply a nonempty, versioned NS 4102 catalogue.", error=True
        )
        return report
    report.checks["catalogue"] = "passed"
    try:
        document = _document(mappings)
        rows = document.get("mappings")
        if not isinstance(rows, list) or not rows:
            raise ValueError("No mappings")
    except (ValueError, UnicodeError, RecursionError):
        report.checks["mappings"] = "failed"
        report.add("MAPPINGS_INVALID", "Supply a nonempty, versioned account mapping document.")
        return report

    report.checks["mappings"] = "passed"
    seen = set()
    known = set(codes)
    for index, row in enumerate(rows):
        path = f"/mappings/{index}"
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("account_id"), str)
            or not row["account_id"].strip()
            or not isinstance(row.get("standard_account"), str)
        ):
            report.add("MAPPING_INVALID", "Each mapping needs two nonempty string IDs.", path=path)
            continue
        if row["account_id"] in seen:
            report.add("ACCOUNT_DUPLICATE", "A local account may only be mapped once.", path=path)
        seen.add(row["account_id"])
        if row["standard_account"] not in known:
            report.add(
                "NS4102_ACCOUNT_UNKNOWN",
                "The target account is absent from the catalogue.",
                path=path,
            )
    if report.status != "valid":
        report.checks["mappings"] = "failed"
    return report
