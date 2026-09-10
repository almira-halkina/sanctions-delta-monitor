from __future__ import annotations

import pytest

from regdelta.normalize import (
    HIGH_OPACITY_JURISDICTIONS,
    classify_program,
    strip_legal_form,
    to_iso2,
    transliteration_key,
)


@pytest.mark.parametrize("a,b", [
    ("Yevgeniy Zhuravlyov", "Evgenii Juravlev"),
    ("Yevgeniy Zhuravlyov", "Evgeny Zhuravlev"),
    ("Dmitrii Shchukin", "Dmitry Schukin"),
])
def test_transliteration_variants_collapse(a, b):
    assert transliteration_key(a) == transliteration_key(b)


@pytest.mark.parametrize("a,b", [
    ("Yevgeniy Zhuravlyov", "Mikhail Baranov"),
    ("OOO Titan", "OOO Titanium Works"),
])
def test_distinct_names_do_not_collapse(a, b):
    assert transliteration_key(a) != transliteration_key(b)


@pytest.mark.parametrize("a,b", [
    ("OOO Titan Logistika", "Titan Logistika LLC"),
    ("Publichnoe Aktsionernoe Obshchestvo Volna", "Volna PJSC"),
])
def test_legal_form_is_stripped_from_either_end(a, b):
    assert strip_legal_form(a) == strip_legal_form(b)


def test_unrecognised_country_returns_empty_not_a_guess():
    assert to_iso2("Ruritania") == ""
    assert to_iso2("Russian Federation") == "RU"
    assert to_iso2("CN") == "CN"


def test_program_taxonomy():
    assert classify_program("RUSSIA-EO14024") == ("US/OFAC Russia-Ukraine", "RU")
    assert classify_program("BELARUS-EO14038") == ("US/OFAC Belarus", "BY")
    assert classify_program("Entity List (EL)")[0] == "US/BIS Entity List"
    assert classify_program("SOMETHING-NEW") == ("unclassified", "")


def test_reexport_hubs_are_flagged_high_opacity():
    for jurisdiction in ("AE", "TR", "KZ", "HK", "CY"):
        assert jurisdiction in HIGH_OPACITY_JURISDICTIONS
