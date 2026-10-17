from football_pipeline.raw import content_hash


def test_hash_ignores_key_order():
    assert content_hash({"a": 1, "b": [1, 2]}) == content_hash({"b": [1, 2], "a": 1})


def test_hash_changes_with_content():
    assert content_hash({"a": 1}) != content_hash({"a": 2})


def test_hash_is_hex_sha256():
    assert len(content_hash([])) == 64
