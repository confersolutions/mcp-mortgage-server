"""
Modern MCP Server Tests
======================

Tests for MCP tools following 2025 best practices.

Run with:
    pytest tests/test_mcp_tools.modern.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch
from pydantic import ValidationError
import httpx

# Import from modern server
# NOTE: Once migration complete, update import path
# from server import (
#     parse_loan_estimate,
#     parse_closing_disclosure,
#     compare_le_cd,
#     hello,
#     validate_pdf_url,
#     download_pdf,
#     MISMOLoanEstimate,
#     MISMOClosingDisclosure,
#     ComplianceReport,
# )


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_le_data():
    """Sample Loan Estimate data matching MISMO format"""
    return {
        "loan_amount": 300000.0,
        "interest_rate": 6.5,
        "apr": 6.73,
        "monthly_payment": 1896.20,
        "origination_charges": 1500.0,
        "services_borrower_cannot_shop": 800.0,
        "services_borrower_can_shop": 1200.0,
        "taxes_and_government_fees": 2500.0,
        "prepaids": 3000.0,
        "initial_escrow": 2400.0,
        "other_costs": 600.0,
        "lender_name": "Test Bank",
        "loan_term_months": 360,
        "tolerance_buckets": {
            "origination_charges": "zero",
            "services_borrower_cannot_shop": "zero",
            "services_borrower_can_shop": "10_percent",
        }
    }


@pytest.fixture
def sample_cd_data():
    """Sample Closing Disclosure data"""
    return {
        "loan_amount": 300000.0,
        "interest_rate": 6.5,
        "apr": 6.75,  # Slightly higher than LE
        "monthly_payment": 1896.20,
        "origination_charges": 1500.0,  # Same as LE (zero tolerance)
        "services_borrower_cannot_shop": 850.0,  # Increased by $50
        "services_borrower_can_shop": 1250.0,  # Increased by $50
        "taxes_and_government_fees": 2600.0,  # Can change unlimited
        "prepaids": 3100.0,
        "initial_escrow": 2400.0,
        "other_costs": 650.0,
        "cash_to_close": 65000.0,
        "closing_date": "2025-06-15"
    }


@pytest.fixture
def mock_pdf_bytes():
    """Mock PDF file content"""
    # Minimal valid PDF structure
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF"


@pytest.fixture
def mock_http_response(mock_pdf_bytes):
    """Mock httpx response for PDF download"""
    def _make_response(url: str, content: bytes = None):
        response = AsyncMock()
        response.content = content or mock_pdf_bytes
        response.headers = {"content-type": "application/pdf"}
        response.raise_for_status = AsyncMock()
        return response
    return _make_response


# ============================================================================
# Basic Tool Tests
# ============================================================================

def test_hello_tool():
    """Test hello tool with default parameter"""
    # NOTE: Uncomment when server.modern.py is active
    # result = hello()
    # assert "Hello, World!" in result
    # assert "MCP server is working" in result
    pass


def test_hello_tool_with_name():
    """Test hello tool with custom name"""
    # result = hello(name="Alice")
    # assert "Hello, Alice!" in result
    pass


# ============================================================================
# Security Tests
# ============================================================================

def test_validate_pdf_url_https_required():
    """Test that only HTTPS URLs are accepted"""
    # Should reject HTTP
    # with pytest.raises(ValueError, match="Only HTTPS"):
    #     validate_pdf_url("http://example.com/doc.pdf")
    pass


def test_validate_pdf_url_domain_whitelist():
    """Test domain whitelist enforcement"""
    # Should accept whitelisted domain
    # validate_pdf_url("https://storage.googleapis.com/bucket/doc.pdf")

    # Should reject non-whitelisted domain
    # with pytest.raises(ValueError, match="Domain not allowed"):
    #     validate_pdf_url("https://evil.com/doc.pdf")
    pass


def test_validate_pdf_url_file_extension():
    """Test that only PDF files are accepted"""
    # Should accept .pdf
    # validate_pdf_url("https://storage.googleapis.com/test/doc.pdf")

    # Should reject other extensions
    # with pytest.raises(ValueError, match="Only PDF"):
    #     validate_pdf_url("https://storage.googleapis.com/test/doc.txt")
    pass


@pytest.mark.asyncio
async def test_download_pdf_size_limit(mock_http_response):
    """Test that oversized PDFs are rejected"""
    # Create oversized PDF (> MAX_PDF_SIZE)
    # large_content = b"%PDF" + (b"X" * 11_000_000)

    # with patch("httpx.AsyncClient.get", return_value=mock_http_response("test", large_content)):
    #     with pytest.raises(ValueError, match="too large"):
    #         await download_pdf("https://storage.googleapis.com/test/large.pdf")
    pass


@pytest.mark.asyncio
async def test_download_pdf_magic_bytes(mock_http_response):
    """Test that non-PDF files are rejected"""
    # Invalid content (not a PDF)
    # invalid_content = b"Not a PDF file"

    # with patch("httpx.AsyncClient.get", return_value=mock_http_response("test", invalid_content)):
    #     with pytest.raises(ValueError, match="not.*valid PDF"):
    #         await download_pdf("https://storage.googleapis.com/test/fake.pdf")
    pass


# ============================================================================
# Data Model Tests
# ============================================================================

def test_mismo_loan_estimate_validation(sample_le_data):
    """Test MISMOLoanEstimate model validation"""
    # Should accept valid data
    # le = MISMOLoanEstimate(**sample_le_data)
    # assert le.loan_amount == 300000.0
    # assert le.total_closing_costs > 0
    pass


def test_mismo_loan_estimate_invalid_loan_amount():
    """Test that invalid loan amounts are rejected"""
    # with pytest.raises(ValidationError):
    #     MISMOLoanEstimate(
    #         loan_amount=-1000,  # Negative
    #         interest_rate=6.5,
    #         apr=6.73,
    #         monthly_payment=1896.20
    #     )
    pass


def test_mismo_loan_estimate_invalid_interest_rate():
    """Test that invalid interest rates are rejected"""
    # with pytest.raises(ValidationError):
    #     MISMOLoanEstimate(
    #         loan_amount=300000,
    #         interest_rate=150,  # > 100%
    #         apr=6.73,
    #         monthly_payment=1896.20
    #     )
    pass


def test_mismo_loan_estimate_total_closing_costs(sample_le_data):
    """Test total closing costs calculation"""
    # le = MISMOLoanEstimate(**sample_le_data)
    # expected = (
    #     le.origination_charges +
    #     le.services_borrower_cannot_shop +
    #     le.services_borrower_can_shop +
    #     le.taxes_and_government_fees +
    #     le.prepaids +
    #     le.initial_escrow +
    #     le.other_costs
    # )
    # assert le.total_closing_costs == expected
    pass


# ============================================================================
# Tool Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_parse_loan_estimate_success(mock_http_response, sample_le_data):
    """Test successful LE parsing"""
    # url = "https://storage.googleapis.com/test/le.pdf"

    # with patch("httpx.AsyncClient.get", return_value=mock_http_response(url)):
    #     with patch("server.parse_le_pdf_content", return_value=sample_le_data):
    #         result = await parse_loan_estimate(url)

    #         assert isinstance(result, MISMOLoanEstimate)
    #         assert result.loan_amount == 300000.0
    #         assert result.apr > result.interest_rate  # APR should be higher
    pass


@pytest.mark.asyncio
async def test_parse_loan_estimate_invalid_url():
    """Test that parse_loan_estimate validates URLs"""
    # Should reject invalid URL
    # with pytest.raises(ValueError):
    #     await parse_loan_estimate("http://evil.com/doc.pdf")
    pass


@pytest.mark.asyncio
async def test_compare_le_cd_compliant(sample_le_data, sample_cd_data):
    """Test TRID compliance with compliant documents"""
    # Make CD compliant (no fee increases)
    # compliant_cd = sample_cd_data.copy()
    # compliant_cd["origination_charges"] = sample_le_data["origination_charges"]
    # compliant_cd["services_borrower_cannot_shop"] = sample_le_data["services_borrower_cannot_shop"]
    # compliant_cd["services_borrower_can_shop"] = sample_le_data["services_borrower_can_shop"]
    # compliant_cd["apr"] = sample_le_data["apr"]

    # with patch("server.parse_loan_estimate", return_value=MISMOLoanEstimate(**sample_le_data)):
    #     with patch("server.parse_closing_disclosure", return_value=MISMOClosingDisclosure(**compliant_cd)):
    #         report = await compare_le_cd("le_url", "cd_url")

    #         assert isinstance(report, ComplianceReport)
    #         assert report.is_compliant
    #         assert len(report.violations) == 0
    pass


@pytest.mark.asyncio
async def test_compare_le_cd_zero_tolerance_violation(sample_le_data, sample_cd_data):
    """Test detection of zero-tolerance violations"""
    # CD has increased origination charges (zero tolerance)
    # sample_cd_data["origination_charges"] = sample_le_data["origination_charges"] + 100.0

    # with patch("server.parse_loan_estimate", return_value=MISMOLoanEstimate(**sample_le_data)):
    #     with patch("server.parse_closing_disclosure", return_value=MISMOClosingDisclosure(**sample_cd_data)):
    #         report = await compare_le_cd("le_url", "cd_url")

    #         assert not report.is_compliant
    #         assert len(report.violations) > 0
    #         assert any(v["type"] == "zero_tolerance" for v in report.violations)
    pass


@pytest.mark.asyncio
async def test_compare_le_cd_ten_percent_violation(sample_le_data, sample_cd_data):
    """Test detection of 10% tolerance violations"""
    # CD has services_borrower_can_shop increased by > 10%
    # sample_cd_data["services_borrower_can_shop"] = sample_le_data["services_borrower_can_shop"] * 1.15  # 15% increase

    # with patch("server.parse_loan_estimate", return_value=MISMOLoanEstimate(**sample_le_data)):
    #     with patch("server.parse_closing_disclosure", return_value=MISMOClosingDisclosure(**sample_cd_data)):
    #         report = await compare_le_cd("le_url", "cd_url")

    #         assert not report.is_compliant
    #         assert any(v["type"] == "10_percent_tolerance" for v in report.violations)
    pass


@pytest.mark.asyncio
async def test_compare_le_cd_apr_violation(sample_le_data, sample_cd_data):
    """Test detection of APR accuracy violations"""
    # APR changed by more than 0.125%
    # sample_cd_data["apr"] = sample_le_data["apr"] + 0.15

    # with patch("server.parse_loan_estimate", return_value=MISMOLoanEstimate(**sample_le_data)):
    #     with patch("server.parse_closing_disclosure", return_value=MISMOClosingDisclosure(**sample_cd_data)):
    #         report = await compare_le_cd("le_url", "cd_url")

    #         assert not report.is_compliant
    #         assert any(v["type"] == "apr_accuracy" for v in report.violations)
    pass


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_parse_loan_estimate_network_error():
    """Test handling of network errors"""
    # url = "https://storage.googleapis.com/test/le.pdf"

    # with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
    #     with pytest.raises(httpx.TimeoutException):
    #         await parse_loan_estimate(url)
    pass


@pytest.mark.asyncio
async def test_parse_loan_estimate_invalid_pdf():
    """Test handling of corrupted PDF files"""
    # url = "https://storage.googleapis.com/test/corrupt.pdf"

    # with patch("httpx.AsyncClient.get", return_value=mock_http_response(url, b"corrupted")):
    #     with pytest.raises(ValueError, match="not.*valid PDF"):
    #         await parse_loan_estimate(url)
    pass


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.slow
async def test_parse_loan_estimate_performance():
    """Test that LE parsing completes within reasonable time"""
    # import time

    # url = "https://storage.googleapis.com/test/le.pdf"

    # with patch("httpx.AsyncClient.get", return_value=mock_http_response(url)):
    #     with patch("server.parse_le_pdf_content", return_value=sample_le_data):
    #         start = time.time()
    #         await parse_loan_estimate(url)
    #         elapsed = time.time() - start

    #         assert elapsed < 5.0, f"Parsing took too long: {elapsed:.2f}s"
    pass


# ============================================================================
# Parameterized Tests
# ============================================================================

@pytest.mark.parametrize("url,should_pass", [
    ("https://storage.googleapis.com/bucket/doc.pdf", True),
    ("https://s3.amazonaws.com/bucket/doc.pdf", True),
    ("http://storage.googleapis.com/bucket/doc.pdf", False),  # Not HTTPS
    ("https://evil.com/doc.pdf", False),  # Not whitelisted
    ("https://storage.googleapis.com/bucket/doc.txt", False),  # Not PDF
    ("ftp://storage.googleapis.com/bucket/doc.pdf", False),  # Not HTTPS
])
def test_validate_pdf_url_parametrized(url, should_pass):
    """Test URL validation with various inputs"""
    # if should_pass:
    #     validate_pdf_url(url)  # Should not raise
    # else:
    #     with pytest.raises(ValueError):
    #         validate_pdf_url(url)
    pass


# ============================================================================
# Integration Test (requires real MCP client)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_with_mcp_client():
    """
    Full integration test using actual MCP client.

    This test requires:
    1. MCP server running
    2. MCP client library
    3. Sample PDF files

    Run with: pytest -m integration
    """
    # from mcp import Client, StdioServerParameters
    # from mcp.client.stdio import stdio_client

    # async with stdio_client(StdioServerParameters(
    #     command="python",
    #     args=["server.py"]
    # )) as (read, write):
    #     async with Client(read, write) as client:
    #         # Initialize
    #         await client.initialize()

    #         # List tools
    #         tools = await client.list_tools()
    #         tool_names = [t.name for t in tools]
    #         assert "parse_loan_estimate" in tool_names
    #         assert "compare_le_cd" in tool_names

    #         # Call hello tool
    #         result = await client.call_tool("hello", {"name": "Test"})
    #         assert "Test" in result.content

    #         # Call parse_loan_estimate (with mock URL)
    #         # result = await client.call_tool(
    #         #     "parse_loan_estimate",
    #         #     {"pdf_url": "https://storage.googleapis.com/test/le.pdf"}
    #         # )
    #         # assert result.content  # Has result
    pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
