"""
Validator tests for the notebooks module.
"""

import tempfile
import os
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from ..utils.validators import (
    FileValidator,
    URLValidator,
    validate_file_type,
    get_content_type_for_extension,
    sanitize_filename
)


class FileValidatorTests(TestCase):
    """Test cases for FileValidator."""

    def setUp(self):
        self.validator = FileValidator()

    def test_valid_file_upload(self):
        """Test validation of a valid file upload."""
        # Create a simple text file
        file_content = b"This is test content for a text file."
        uploaded_file = SimpleUploadedFile(
            "test.txt", file_content, content_type="text/plain"
        )

        result = self.validator.validate_file(uploaded_file)
        
        self.assertTrue(result["valid"])
        self.assertEqual(result["file_extension"], ".txt")
        self.assertEqual(result["content_type"], "text/plain")
        self.assertEqual(len(result["errors"]), 0)

    def test_file_size_validation(self):
        """Test file size validation."""
        # Create a file that exceeds the size limit
        large_content = b"x" * (101 * 1024 * 1024)  # 101MB
        uploaded_file = SimpleUploadedFile(
            "large.txt", large_content, content_type="text/plain"
        )

        result = self.validator.validate_file(uploaded_file)
        
        self.assertFalse(result["valid"])
        self.assertTrue(any("File size" in error for error in result["errors"]))

    def test_unsupported_file_extension(self):
        """Test validation of unsupported file extension."""
        file_content = b"This is test content."
        uploaded_file = SimpleUploadedFile(
            "test.exe", file_content, content_type="application/x-executable"
        )

        result = self.validator.validate_file(uploaded_file)
        
        self.assertFalse(result["valid"])
        self.assertTrue(any("not allowed" in error for error in result["errors"]))

    def test_missing_file(self):
        """Test validation with no file provided."""
        result = self.validator.validate_file(None)
        
        self.assertFalse(result["valid"])
        self.assertTrue(any("No file provided" in error for error in result["errors"]))

    def test_file_without_name(self):
        """Test validation of file without name."""
        file_content = b"Test content"
        uploaded_file = SimpleUploadedFile(
            "", file_content, content_type="text/plain"
        )

        result = self.validator.validate_file(uploaded_file)
        
        self.assertFalse(result["valid"])

    def test_content_type_mismatch_warning(self):
        """Test content type mismatch generates warning."""
        file_content = b"This is text content."
        uploaded_file = SimpleUploadedFile(
            "test.txt", file_content, content_type="application/pdf"  # Wrong content type
        )

        result = self.validator.validate_file(uploaded_file)
        
        # Should still be valid but with warnings
        self.assertTrue(result["valid"])
        self.assertGreater(len(result["warnings"]), 0)

    def test_validate_file_content_with_temp_file(self):
        """Test file content validation with temporary file."""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is test content")
            temp_path = f.name

        try:
            result = self.validator.validate_file_content(temp_path)
            self.assertTrue(result["valid"])
            self.assertEqual(len(result["errors"]), 0)
        finally:
            os.unlink(temp_path)

    def test_validate_nonexistent_file_content(self):
        """Test file content validation with nonexistent file."""
        result = self.validator.validate_file_content("/nonexistent/file.txt")
        
        self.assertFalse(result["valid"])
        self.assertTrue(any("does not exist" in error for error in result["errors"]))


class URLValidatorTests(TestCase):
    """Test cases for URLValidator."""

    def setUp(self):
        self.validator = URLValidator()

    def test_valid_url(self):
        """Test validation of a valid URL."""
        valid_urls = [
            "https://example.com",
            "http://example.com/path",
            "https://subdomain.example.com/path?query=value"
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                result = self.validator.validate_url(url)
                self.assertTrue(result["valid"], f"URL {url} should be valid")
                self.assertEqual(len(result["errors"]), 0)

    def test_invalid_url_format(self):
        """Test validation of invalid URL formats."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Unsupported scheme
            "javascript:alert('xss')",
            ""
        ]

        for url in invalid_urls:
            with self.subTest(url=url):
                result = self.validator.validate_url(url)
                self.assertFalse(result["valid"], f"URL {url} should be invalid")

    def test_blocked_domains(self):
        """Test validation of blocked domains."""
        blocked_urls = [
            "http://localhost/path",
            "https://127.0.0.1/test",
            "http://0.0.0.0:8000"
        ]

        for url in blocked_urls:
            with self.subTest(url=url):
                result = self.validator.validate_url(url)
                self.assertFalse(result["valid"], f"URL {url} should be blocked")
                self.assertTrue(any("blocked" in error.lower() for error in result["errors"]))

    def test_private_network_warning(self):
        """Test that private network URLs generate warnings."""
        private_urls = [
            "http://192.168.1.1/test",
            "https://10.0.0.1/path"
        ]

        for url in private_urls:
            with self.subTest(url=url):
                result = self.validator.validate_url(url)
                # Might be valid but should have warnings
                self.assertGreater(len(result["warnings"]), 0)

    def test_empty_url(self):
        """Test validation with empty URL."""
        result = self.validator.validate_url("")
        
        self.assertFalse(result["valid"])
        self.assertTrue(any("No URL provided" in error for error in result["errors"]))


class UtilityFunctionTests(TestCase):
    """Test cases for utility functions."""

    def test_validate_file_type(self):
        """Test validate_file_type function."""
        # Valid file types
        self.assertTrue(validate_file_type("document.pdf"))
        self.assertTrue(validate_file_type("text.txt"))
        self.assertTrue(validate_file_type("audio.mp3"))
        self.assertTrue(validate_file_type("video.mp4"))

        # Invalid file types
        self.assertFalse(validate_file_type("executable.exe"))
        self.assertFalse(validate_file_type("script.bat"))
        self.assertFalse(validate_file_type("archive.zip"))

    def test_get_content_type_for_extension(self):
        """Test get_content_type_for_extension function."""
        test_cases = [
            (".pdf", "application/pdf"),
            (".txt", "text/plain"),
            (".md", "text/markdown"),
            (".mp3", "audio/mpeg"),
            (".mp4", "video/mp4"),
            (".unknown", "application/octet-stream")  # Default for unknown
        ]

        for extension, expected_type in test_cases:
            with self.subTest(extension=extension):
                result = get_content_type_for_extension(extension)
                self.assertEqual(result, expected_type)

    def test_sanitize_filename(self):
        """Test sanitize_filename function."""
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file with spaces.pdf", "file with spaces.pdf"),
            ("file<>:\"\\|?*/.txt", "file_______/.txt"),  # Problematic chars replaced
            ("very_long_filename_" + "x" * 300 + ".txt", None),  # Should be truncated
            ("../../../etc/passwd", "passwd"),  # Path traversal removed
        ]

        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = sanitize_filename(input_name)
                if expected is None:
                    # Check that it was truncated to reasonable length
                    self.assertLessEqual(len(result), 255)
                    self.assertTrue(result.endswith(".txt"))
                else:
                    self.assertEqual(result, expected) 