"""Normalisation of the fields that regulators spell inconsistently.

The three that matter for change detection:

**Country.** OFAC writes country names in prose ("Russia", "Russian
Federation", "Korea, North"). BIS/CSL emits ISO alpha-2. The EU emits ISO
alpha-2 but occasionally leaves it blank and puts the country in the address
line. Without a single representation, the same address reads as an amendment
every time a source changes hands.

**Program.** OFAC program tags are versioned by executive order
("RUSSIA-EO14024", "UKRAINE-EO13662"). The EU tags by programme code ("RUS",
"BLR"). BIS does not tag programs at all; the restriction lives in the licence
requirement text. Mapping these onto one authority taxonomy is what makes
"which programme drove today's activity" answerable across sources.

**Name.** Cyrillic-script targets reach the lists through whichever
transliteration the filer used. Yevgeniy / Evgeniy / Evgenii / Eugene are the
same first name; Zhuravlyov / Zhuravlev / Juravlov the same surname. The
folding here is deliberately lossy and deliberately conservative: it exists to
recognise that two spellings *may* be the same string for alias-drift
detection, not to assert identity. Anything stronger belongs in a record-linkage
model with a scored threshold, not in a normaliser.
"""

from __future__ import annotations

import re
import unicodedata

# --------------------------------------------------------------------------
# Country
# --------------------------------------------------------------------------

_COUNTRY_TO_ISO2: dict[str, str] = {
    "russia": "RU",
    "russian federation": "RU",
    "belarus": "BY",
    "republic of belarus": "BY",
    "china": "CN",
    "china, people's republic of": "CN",
    "people's republic of china": "CN",
    "hong kong": "HK",
    "iran": "IR",
    "iran, islamic republic of": "IR",
    "korea, north": "KP",
    "north korea": "KP",
    "united arab emirates": "AE",
    "turkey": "TR",
    "turkiye": "TR",
    "kazakhstan": "KZ",
    "kyrgyzstan": "KG",
    "armenia": "AM",
    "georgia": "GE",
    "cyprus": "CY",
    "netherlands": "NL",
    "germany": "DE",
    "united kingdom": "GB",
    "united states": "US",
    "singapore": "SG",
    "india": "IN",
    "malaysia": "MY",
    "seychelles": "SC",
    "british virgin islands": "VG",
    "virgin islands, british": "VG",
    "marshall islands": "MH",
    "panama": "PA",
    "ukraine": "UA",
    "estonia": "EE",
    "latvia": "LV",
    "lithuania": "LT",
    "poland": "PL",
    "moldova": "MD",
    "azerbaijan": "AZ",
    "uzbekistan": "UZ",
    "tajikistan": "TJ",
    "serbia": "RS",
    "pakistan": "PK",
    "afghanistan": "AF",
    "iraq": "IQ",
    "yemen": "YE",
    "mali": "ML",
    "algeria": "DZ",
    "sudan": "SD",
    "south sudan": "SS",
    "congo, democratic republic of the": "CD",
    "lebanon": "LB",
    "mexico": "MX",
    "colombia": "CO",
    "egypt": "EG",
    "libya": "LY",
    "somalia": "SO",
    "nicaragua": "NI",
    "switzerland": "CH",
    "italy": "IT",
    "israel": "IL",
    "vietnam": "VN",
    "thailand": "TH",
    "syria": "SY",
    "venezuela": "VE",
    "cuba": "CU",
    "myanmar": "MM",
    "burma": "MM",
}

_ISO2_TO_NAME: dict[str, str] = {
    "RU": "Russia",
    "BY": "Belarus",
    "CN": "China",
    "HK": "Hong Kong",
    "IR": "Iran",
    "KP": "North Korea",
    "AE": "United Arab Emirates",
    "TR": "Turkiye",
    "KZ": "Kazakhstan",
    "KG": "Kyrgyzstan",
    "AM": "Armenia",
    "GE": "Georgia",
    "CY": "Cyprus",
    "NL": "Netherlands",
    "DE": "Germany",
    "GB": "United Kingdom",
    "US": "United States",
    "SG": "Singapore",
    "IN": "India",
    "MY": "Malaysia",
    "SC": "Seychelles",
    "VG": "British Virgin Islands",
    "MH": "Marshall Islands",
    "PA": "Panama",
    "UA": "Ukraine",
    "EE": "Estonia",
    "LV": "Latvia",
    "LT": "Lithuania",
    "PL": "Poland",
    "MD": "Moldova",
    "AZ": "Azerbaijan",
    "UZ": "Uzbekistan",
    "TJ": "Tajikistan",
    "RS": "Serbia",
    "PK": "Pakistan",
    "AF": "Afghanistan",
    "IQ": "Iraq",
    "YE": "Yemen",
    "ML": "Mali",
    "DZ": "Algeria",
    "SD": "Sudan",
    "SS": "South Sudan",
    "CD": "DR Congo",
    "LB": "Lebanon",
    "MX": "Mexico",
    "CO": "Colombia",
    "EG": "Egypt",
    "LY": "Libya",
    "SO": "Somalia",
    "NI": "Nicaragua",
    "CH": "Switzerland",
    "IT": "Italy",
    "IL": "Israel",
    "VN": "Vietnam",
    "TH": "Thailand",
    "SY": "Syria",
    "VE": "Venezuela",
    "CU": "Cuba",
    "MM": "Myanmar",
}

#: Jurisdictions where a designation is most likely to have an ownership tail
#: that the published lists do not show -- either because the corporate
#: register is closed, or because the jurisdiction is a known re-export or
#: incorporation node for Russia/Iran/DPRK procurement.
HIGH_OPACITY_JURISDICTIONS: frozenset[str] = frozenset(
    {"RU", "BY", "CN", "HK", "AE", "TR", "KZ", "KG", "AM", "GE", "CY", "SC", "VG", "MH", "PA"}
)


def to_iso2(value: str) -> str:
    """Best-effort ISO 3166-1 alpha-2. Returns '' when unrecognised.

    Unrecognised is returned rather than guessed: a wrong country code
    propagates into jurisdiction counts in the brief, and a silently wrong
    number in an analyst-facing product is worse than a visible gap.
    """
    if not value:
        return ""
    v = value.strip()
    if len(v) == 2 and v.isalpha() and v.isupper():
        return v
    return _COUNTRY_TO_ISO2.get(v.casefold(), "")


def country_name(iso2: str) -> str:
    return _ISO2_TO_NAME.get(iso2, iso2)


# --------------------------------------------------------------------------
# Programme -> authority taxonomy
# --------------------------------------------------------------------------

#: (matcher, authority, target jurisdiction). Ordered: first match wins.
_PROGRAM_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"^RUSSIA|^UKRAINE|^RU\b|^RUS$"), "US/OFAC Russia-Ukraine", "RU"),
    (re.compile(r"^BELARUS|^BLR$|^BY$"), "US/OFAC Belarus", "BY"),
    (re.compile(r"^IRAN|^IFSR|^IRGC|^IRN$"), "US/OFAC Iran", "IR"),
    (re.compile(r"^DPRK|^NPWMD|^KP$"), "US/OFAC DPRK & WMD", "KP"),
    (re.compile(r"^CHINA|^CMIC|^NS-CMIC|^CN$"), "US/OFAC China military-industrial", "CN"),
    (re.compile(r"^SDGT|^FTO|^SDT|^TCO"), "US/OFAC counter-terrorism", ""),
    (re.compile(r"^SDNTK?|^ILLICIT-DRUGS"), "US/OFAC counter-narcotics", ""),
    (re.compile(r"^GLOMAG|^HRIT"), "US/OFAC human rights", ""),
    (re.compile(r"^SYRIA|^SYR$"), "US/OFAC Syria", "SY"),
    (re.compile(r"^VENEZUELA|^VEN$"), "US/OFAC Venezuela", "VE"),
    (re.compile(r"^ENTITY LIST|^EL$"), "US/BIS Entity List", ""),
    (re.compile(r"^MEU|^MILITARY END USER"), "US/BIS Military End User", ""),
    (re.compile(r"^UVL|^UNVERIFIED"), "US/BIS Unverified List", ""),
    (re.compile(r"^DPL|^DENIED"), "US/BIS Denied Persons", ""),
)


def classify_program(program: str) -> tuple[str, str]:
    """Map a raw programme tag to (authority, target jurisdiction ISO2)."""
    p = program.strip().upper()
    for pattern, authority, jurisdiction in _PROGRAM_RULES:
        if pattern.search(p):
            return authority, jurisdiction
    return "unclassified", ""


# --------------------------------------------------------------------------
# Names
# --------------------------------------------------------------------------

# Longest first: the loop below strips repeatedly, but a full Russian legal
# form is not a suffix of its abbreviated cousin, so each spelled-out variant
# has to be listed in its own right.
_LEGAL_SUFFIXES = (
    "publichnoe aktsionernoe obshchestvo",
    "publichnoye aktsionernoye obshchestvo",
    "otkrytoe aktsionernoe obshchestvo",
    "zakrytoe aktsionernoe obshchestvo",
    "obshchestvo s ogranichennoy otvetstvennostyu",
    "aktsionernoe obshchestvo",
    "limited liability company",
    "joint stock company",
    "public joint stock company",
    "open joint stock company",
    "closed joint stock company",
    "obshchestvo s ogranichennoi otvetstvennostyu",
    "aktsionernoye obshchestvo",
    "incorporated",
    "corporation",
    "company",
    "limited",
    "gmbh",
    "s.a.r.l",
    "sarl",
    "b.v.",
    "bv",
    "n.v.",
    "nv",
    "ltd",
    "llc",
    "plc",
    "inc",
    "co",
    "ooo",
    "oao",
    "zao",
    "pao",
    "ao",
    "jsc",
    "pjsc",
    "ojsc",
    "cjsc",
    "fze",
    "fzco",
    "dmcc",
    "pte",
    "sdn bhd",
)

_TRANSLIT_FOLDINGS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Order matters: longer digraphs first.
    (re.compile(r"shch|sch|shh"), "sh"),
    (re.compile(r"x"), "ks"),
    (re.compile(r"kh|ch|h"), "h"),
    (re.compile(r"zh|j"), "z"),
    (re.compile(r"ts|tz|c"), "ts"),
    (re.compile(r"yu|iu|ju"), "u"),
    (re.compile(r"ya|ia|ja"), "a"),
    (re.compile(r"ye|ie|je|e"), "e"),
    (re.compile(r"yo|io|jo"), "o"),
    (re.compile(r"ii|iy|yi|ij|y"), "i"),
    (re.compile(r"ov$|ev$|off$|eff$"), "ov"),
    (re.compile(r"aya$|aja$|ay$"), "a"),
)


def strip_diacritics(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_name(value: str) -> str:
    """Casefold, strip punctuation and diacritics, collapse whitespace."""
    if not value:
        return ""
    v = strip_diacritics(value).casefold()
    v = re.sub(r"[^\w\s]", " ", v, flags=re.UNICODE)
    return re.sub(r"\s+", " ", v).strip()


def strip_legal_form(value: str) -> str:
    """Remove corporate-form tokens so 'X LLC' and 'OOO X' compare equal.

    Applied to both ends of the string because Anglophone registers suffix the
    form and Russian-language sources prefix it.
    """
    v = normalize_name(value)
    changed = True
    while changed:
        changed = False
        for suffix in _LEGAL_SUFFIXES:
            if v.endswith(" " + suffix):
                v = v[: -(len(suffix) + 1)].strip()
                changed = True
            if v.startswith(suffix + " "):
                v = v[len(suffix) + 1 :].strip()
                changed = True
    return v


def transliteration_key(value: str) -> str:
    """Aggressively folded key for spotting transliteration variants.

    `Yevgeniy Zhuravlyov` and `Evgenii Juravlev` collapse to the same key. This
    is a *recall* device: it will happily collide unrelated short names, so it
    is only ever used to flag alias drift for analyst review, never to assert
    that two records are the same party.
    """
    v = strip_legal_form(value)
    v = v.replace(" ", "")
    for pattern, replacement in _TRANSLIT_FOLDINGS:
        v = pattern.sub(replacement, v)
    v = re.sub(r"(.)\1+", r"\1", v)  # collapse doubled letters
    return v


def is_cyrillic(value: str) -> bool:
    return any("Ѐ" <= ch <= "ӿ" for ch in value)
