from app.domains.infrastructure.extractors.plain_text import PlainTextExtractor

def test_plain_text_extractor_valid_utf8():
    extractor = PlainTextExtractor()
    assert extractor.extract(b"Hello, World!", "test.txt") == "Hello, World!"

def test_plain_text_extractor_invalid_utf8_replaces_errors():
    extractor = PlainTextExtractor()
    result = extractor.extract(b"Hello \xff\xfe World!", "test.txt")
    assert "Hello" in result and "World" in result
    assert "\ufffd" in result

def test_plain_text_extractor_strips_whitespace():
    extractor = PlainTextExtractor()
    assert extractor.extract(b"   \n\n  Trimmed Text  \n\n   ", "test.txt") == "Trimmed Text"
