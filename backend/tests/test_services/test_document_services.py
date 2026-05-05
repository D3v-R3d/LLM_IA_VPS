import pytest
from app.services.document.text_extraction import TextExtractionService
from app.services.document.text_cleaning import TextCleaningService
from app.services.document.ocr import OCRService


class TestTextExtractionService:
    """Tests for TextExtractionService."""

    @pytest.fixture
    def service(self):
        return TextExtractionService()

    def test_extract_plain_text(self, service):
        """Test extracting plain text."""
        content = "Hello, World!"
        result = service.extract(content, "txt")
        assert result == "Hello, World!"

    def test_extract_markdown(self, service):
        """Test extracting markdown."""
        content = "# Header\n\nSome text"
        result = service.extract(content, "md")
        assert "Header" in result
        assert "Some text" in result

    def test_extract_html(self, service):
        """Test extracting HTML."""
        content = "<html><body><p>Hello</p></body></html>"
        result = service.extract(content, "html")
        assert "Hello" in result
        assert "<" not in result

    def test_extract_html_entities(self, service):
        """Test HTML entity decoding."""
        content = "<p>Tom &amp; Jerry</p>"
        result = service.extract(content, "html")
        assert "Tom" in result
        assert "&" in result

    def test_extract_empty(self, service):
        """Test extracting empty content."""
        assert service.extract("") == ""
        assert service.extract(None) == ""

    def test_detect_type_html(self, service):
        """Test detecting HTML content."""
        assert service._detect_type("<!DOCTYPE html>") == "html"
        assert service._detect_type("<html>") == "html"

    def test_detect_type_pdf(self, service):
        """Test detecting PDF content."""
        assert service._detect_type("%PDF-1.4") == "pdf"

    def test_detect_type_txt(self, service):
        """Test detecting plain text."""
        assert service._detect_type("Just some text") == "txt"

    def test_extract_pdf_placeholder(self, service):
        """Test PDF extraction returns content as-is (placeholder)."""
        content = "%PDF-1.4 some pdf content"
        result = service.extract(content, "pdf")
        assert result == content


class TestTextCleaningService:
    """Tests for TextCleaningService."""

    @pytest.fixture
    def service(self):
        return TextCleaningService()

    def test_clean_basic(self, service):
        """Test basic text cleaning."""
        text = "  Hello   World  "
        result = service.clean(text)
        assert result == "Hello World"

    def test_clean_empty(self, service):
        """Test cleaning empty text."""
        assert service.clean("") == ""
        assert service.clean(None) == ""

    def test_clean_unicode(self, service):
        """Test unicode normalization."""
        text = "café"  # é vs é
        result = service.clean(text)
        assert "café" in result

    def test_clean_control_chars(self, service):
        """Test removing control characters."""
        text = "Hello\x00World"
        result = service.clean(text)
        assert "\x00" not in result
        assert "Hello" in result
        assert "World" in result

    def test_clean_preserves_newlines(self, service):
        """Test that newlines are preserved."""
        text = "Line1\nLine2\n\nLine3"
        result = service.clean(text)
        assert "\n" in result

    def test_clean_removes_extra_newlines(self, service):
        """Test removing excessive newlines."""
        text = "Line1\n\n\n\nLine2"
        result = service.clean(text)
        assert "\n\n\n\n" not in result

    def test_clean_batch(self, service):
        """Test cleaning multiple texts."""
        texts = ["  Hello  ", "  World  "]
        results = service.clean_batch(texts)
        assert results == ["Hello", "World"]

    def test_truncate_short_text(self, service):
        """Test truncate doesn't modify short text."""
        text = "Short"
        result = service.truncate(text, max_length=10)
        assert result == "Short"

    def test_truncate_long_text(self, service):
        """Test truncating long text."""
        text = "A" * 100
        result = service.truncate(text, max_length=10)
        assert len(result) < 100
        assert result.endswith("...")

    def test_truncate_exact_length(self, service):
        """Test truncate with exact max length."""
        text = "Hello"
        result = service.truncate(text, max_length=5)
        assert result == "Hello"


class TestOCRService:
    """Tests for OCRService."""

    @pytest.fixture
    def service(self):
        return OCRService()

    def test_extract_text_returns_error_without_tesseract(self, service):
        """Test that extract_text handles missing tesseract."""
        result = service.extract_text(b"fake image data")
        assert "[OCR unavailable" in result or "error" in result.lower()

    def test_extract_from_pdf_returns_not_implemented(self, service):
        """Test scanned PDF extraction returns placeholder."""
        result = service.extract_from_pdf(b"%PDF-1.4 fake")
        assert "not yet implemented" in result or "OCR" in result

    def test_is_scanned_true(self, service):
        """Test detecting scanned PDF."""
        result = service.is_scanned(b"%PDF-1.4")
        assert result is True

    def test_is_scanned_false(self, service):
        """Test detecting non-scanned content."""
        result = service.is_scanned(b"not a pdf content")
        assert result is False