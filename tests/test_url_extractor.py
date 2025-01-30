# tests/test_url_extractor.py
import pytest
from utils.url_extractor import extract_urls

def test_valid_https_url():
    """Test a valid HTTPS URL"""
    urls, errors = extract_urls("Check out https://example.com")
    assert urls == ["https://example.com"]
    assert not errors

def test_valid_http_url():
    """Test a valid HTTP URL"""
    urls, errors = extract_urls("Check out http://example.com")
    assert urls == ["http://example.com"]
    assert not errors

def test_invalid_url():
    """Test an invalid URL"""
    urls, errors = extract_urls("Visit http://malformed")
    assert not urls
    assert len(errors) == 1
    assert "Invalid URL format" in errors[0]

def test_multiple_urls():
    """Test multiple URLs in one message"""
    urls, errors = extract_urls("Multiple links: https://example.com and http://test.com")
    assert len(urls) == 2
    assert "https://example.com" in urls
    assert "http://test.com" in urls
    assert not errors

def test_non_http_protocol():
    """Test that non-HTTP protocols are ignored"""
    urls, errors = extract_urls("Check ftp://example.com")
    assert not urls
    assert not errors

def test_empty_message():
    """Test empty message"""
    urls, errors = extract_urls("")
    assert not urls
    assert not errors

def test_message_without_urls():
    """Test message with no URLs"""
    urls, errors = extract_urls("Hello world!")
    assert not urls
    assert not errors

def test_mixed_valid_invalid_urls():
    """Test message with both valid and invalid URLs"""
    message = "Check these: https://example.com and http://invalid."
    urls, errors = extract_urls(message)
    assert urls == ["https://example.com"]
    assert len(errors) == 1
    assert "Invalid URL format" in errors[0]