import re

from app.i18n import DEFAULT_LANGUAGE, LANGUAGES, TRANSLATIONS, translate

EXPECTED_LANGUAGES = {"en", "de", "fr", "ru"}
_PLACEHOLDER_RE = re.compile(r"\{[^}]*\}")


def test_default_language_is_english():
    assert DEFAULT_LANGUAGE == "en"
    assert LANGUAGES["en"] == "English"


def test_all_languages_present():
    assert set(LANGUAGES) == EXPECTED_LANGUAGES
    assert set(TRANSLATIONS) == EXPECTED_LANGUAGES


def test_all_languages_share_the_same_keys():
    reference = set(TRANSLATIONS["en"])
    for code, table in TRANSLATIONS.items():
        assert set(table) == reference, f"{code} has different keys"


def test_no_empty_translations():
    for code, table in TRANSLATIONS.items():
        for key, value in table.items():
            assert value.strip(), f"{code}.{key} is empty"


def test_placeholders_match_across_languages():
    for key, english in TRANSLATIONS["en"].items():
        expected = set(_PLACEHOLDER_RE.findall(english))
        for code, table in TRANSLATIONS.items():
            found = set(_PLACEHOLDER_RE.findall(table[key]))
            assert found == expected, f"{code}.{key} placeholders differ"


def test_translate_returns_language_value():
    assert translate("en", "run_button") == TRANSLATIONS["en"]["run_button"]
    assert translate("de", "run_button") != translate("en", "run_button")


def test_translate_falls_back_to_english_for_unknown_language():
    assert translate("zz", "run_button") == TRANSLATIONS["en"]["run_button"]


def test_translate_returns_key_for_missing_key():
    assert translate("en", "does_not_exist") == "does_not_exist"


def test_translate_formats_placeholders():
    assert "1,234" in translate("en", "ok_parsed", count=1234)
    assert "boom" in translate("en", "err_parse", error="boom")


def test_translate_tolerates_missing_kwargs():
    assert "{count" in translate("en", "ok_parsed")
    assert translate("en", "err_parse", nope=1) == TRANSLATIONS["en"]["err_parse"]
