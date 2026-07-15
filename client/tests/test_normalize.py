from app.normalize import normalize_plate


def test_uppercases_lowercase_input():
    assert normalize_plate("a123bc") == "A123BC"


def test_strips_whitespace_and_dashes():
    assert normalize_plate("A 123 - BC") == "A123BC"


def test_maps_cyrillic_lookalikes_to_latin():
    # А(U+0410) В(U+0412) Е(U+0415) К(U+041A) М(U+041C) Н(U+041D)
    # О(U+041E) Р(U+0420) С(U+0421) Т(U+0422) У(U+0423) Х(U+0425)
    assert normalize_plate("А123ВС777") == "A123BC777"
    assert normalize_plate("К777ХА777") == "K777XA777"
    assert normalize_plate("У") == "Y"


def test_leaves_digits_untouched():
    assert normalize_plate("0123456789") == "0123456789"


def test_idempotent_on_already_normalized_latin_plate():
    assert normalize_plate("A123BC777") == "A123BC777"
