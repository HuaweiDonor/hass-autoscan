from app.whitelist import Whitelist


def test_matches_plate_in_list():
    wl = Whitelist(["A123BC777", "K777XA777"])
    assert wl.is_allowed("A123BC777") is True


def test_rejects_plate_not_in_list():
    wl = Whitelist(["A123BC777"])
    assert wl.is_allowed("Z999ZZ999") is False


def test_does_not_fuzzy_match_similar_plate():
    wl = Whitelist(["A123BC777"])
    assert wl.is_allowed("A123BC778") is False


def test_normalizes_input_before_matching():
    # Whitelist entries may be typed with Cyrillic lookalikes or spacing;
    # matching must compare on normalized form both sides.
    wl = Whitelist(["А123ВС777"])  # Cyrillic entry in config
    assert wl.is_allowed("A123BC777") is True  # Latin-normalized OCR read
