import json

import pytest

from agaas_saft.accounts import validate_accounts

# Invented catalogue used only to exercise the interface. No NS 4102 content is asserted here.
CATALOGUE = {"standard": "NS 4102:2023", "source": "synthetic test", "accounts": ["10000", "20000"]}
MAPPINGS = {
    "standard": "NS 4102:2023",
    "mappings": [{"account_id": "local-a", "standard_account": "10000"}],
}


def encode(document):
    return json.dumps(document).encode()


def test_explicit_mapping_to_supplied_catalogue():
    result = validate_accounts(encode(MAPPINGS), catalogue=encode(CATALOGUE))
    assert result.status == "valid"
    assert result.checks == {"catalogue": "passed", "mappings": "passed"}
    assert len(result.metadata["catalogue_sha256"]) == 64


def test_subaccounts_can_share_a_standard_account():
    rows = [*MAPPINGS["mappings"], {"account_id": "local-b", "standard_account": "10000"}]
    result = validate_accounts(encode({**MAPPINGS, "mappings": rows}), catalogue=encode(CATALOGUE))
    assert result.status == "valid"


@pytest.mark.parametrize(
    ("rows", "code"),
    [
        ([{"account_id": "local-a", "standard_account": "80000"}], "NS4102_ACCOUNT_UNKNOWN"),
        ([{"account_id": "local-a", "standard_account": "1000"}], "NS4102_ACCOUNT_UNKNOWN"),
        (MAPPINGS["mappings"] * 2, "ACCOUNT_DUPLICATE"),
        ([{"account_id": "local-a"}], "MAPPING_INVALID"),
        ([{"account_id": 1000, "standard_account": "10000"}], "MAPPING_INVALID"),
        ([], "MAPPINGS_INVALID"),
    ],
)
def test_missing_unknown_duplicate_and_implicit_normalization_fail(rows, code):
    result = validate_accounts(encode({**MAPPINGS, "mappings": rows}), catalogue=encode(CATALOGUE))
    assert result.status == "invalid"
    assert result.issues[0].code == code


@pytest.mark.parametrize(
    "catalogue",
    [
        b"",
        b"{}",
        b"[]",
        b"null",
        b"\xff",
        encode({**CATALOGUE, "accounts": []}),
        encode({**CATALOGUE, "standard": "NS 4102:2005"}),
    ],
)
def test_absent_or_wrong_catalogue_is_an_error_not_a_skipped_check(catalogue):
    result = validate_accounts(encode(MAPPINGS), catalogue=catalogue)
    assert result.status == "error"
    assert result.issues[0].code == "CATALOGUE_INVALID"


def test_duplicate_json_keys_are_rejected():
    mappings = b'{"standard":"NS 4102:2023","mappings":[],"mappings":[]}'
    assert validate_accounts(mappings, catalogue=encode(CATALOGUE)).exit_code == 1
