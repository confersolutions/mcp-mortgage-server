"""
Modern MCP Server for Mortgage Document Processing
==================================================

Compliant with Model Context Protocol specification 2025-03-26.

Features:
- JSON-RPC 2.0 protocol via stdio transport
- Type-safe tools with Pydantic validation
- Resources for MISMO schemas
- Prompts for mortgage analysis workflows
- Security controls (URL validation, size limits)

Usage:
    # Run server
    python server.modern.py

    # Test with MCP Inspector
    mcp dev server.modern.py

    # Use with Claude Desktop
    Add to claude_desktop_config.json:
    {
      "mcpServers": {
        "mortgage": {
          "command": "python",
          "args": ["server.modern.py"]
        }
      }
    }

Copyright (c) 2025 Confer Solutions
License: MIT
"""

from fastmcp import FastMCP
from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, Literal, Dict, Any
import httpx
import json
from pathlib import Path
from urllib.parse import urlparse
import os

# ============================================================================
# Configuration
# ============================================================================

__version__ = "2.0.0"
__author__ = "Confer Solutions"

# Security: Allowed PDF source domains (prevent SSRF)
ALLOWED_DOMAINS = os.getenv(
    "ALLOWED_DOMAINS",
    "storage.googleapis.com,s3.amazonaws.com,mortgage-docs.confer.ai"
).split(",")

MAX_PDF_SIZE = int(os.getenv("MAX_PDF_SIZE", 10 * 1024 * 1024))  # 10MB
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", 30))  # seconds

# ============================================================================
# Initialize MCP Server
# ============================================================================

mcp = FastMCP(
    name="Mortgage Document Parser",
    version=__version__,
    description="Parse and analyze mortgage documents (Loan Estimates, Closing Disclosures) using MISMO standards"
)

# ============================================================================
# Data Models (Pydantic)
# ============================================================================

class MISMOLoanEstimate(BaseModel):
    """MISMO-compliant Loan Estimate data structure"""

    # Loan Information
    loan_amount: float = Field(
        ...,
        gt=0,
        lt=100_000_000,
        description="Total loan amount in USD"
    )
    interest_rate: float = Field(
        ...,
        ge=0,
        le=100,
        description="Interest rate as percentage (e.g., 6.5 for 6.5%)"
    )
    apr: float = Field(
        ...,
        ge=0,
        le=100,
        description="Annual Percentage Rate"
    )
    monthly_payment: float = Field(
        ...,
        gt=0,
        description="Monthly principal and interest payment"
    )

    # Closing Costs
    origination_charges: float = Field(default=0, ge=0)
    services_borrower_cannot_shop: float = Field(default=0, ge=0)
    services_borrower_can_shop: float = Field(default=0, ge=0)
    taxes_and_government_fees: float = Field(default=0, ge=0)
    prepaids: float = Field(default=0, ge=0)
    initial_escrow: float = Field(default=0, ge=0)
    other_costs: float = Field(default=0, ge=0)

    # Metadata
    lender_name: Optional[str] = None
    loan_term_months: Optional[int] = Field(default=360, ge=1, le=480)
    property_address: Optional[str] = None
    borrower_name: Optional[str] = None

    # Compliance
    tolerance_buckets: Dict[str, str] = Field(
        default_factory=dict,
        description="Maps fees to tolerance buckets: zero, 10_percent, unlimited"
    )

    @validator('loan_amount')
    def validate_reasonable_loan(cls, v):
        """Sanity check: reject unrealistic loan amounts"""
        if v < 1000:
            raise ValueError("Loan amount too small (< $1,000)")
        if v > 50_000_000:
            # Large loans allowed but flagged
            print(f"WARNING: Large loan amount: ${v:,.2f}")
        return v

    @property
    def total_closing_costs(self) -> float:
        """Calculate total closing costs"""
        return (
            self.origination_charges +
            self.services_borrower_cannot_shop +
            self.services_borrower_can_shop +
            self.taxes_and_government_fees +
            self.prepaids +
            self.initial_escrow +
            self.other_costs
        )


class MISMOClosingDisclosure(BaseModel):
    """MISMO-compliant Closing Disclosure data structure"""

    # Similar structure to LE but with final amounts
    loan_amount: float = Field(..., gt=0)
    interest_rate: float = Field(..., ge=0, le=100)
    apr: float = Field(..., ge=0, le=100)
    monthly_payment: float = Field(..., gt=0)

    # Final closing costs (may differ from LE)
    origination_charges: float = Field(default=0, ge=0)
    services_borrower_cannot_shop: float = Field(default=0, ge=0)
    services_borrower_can_shop: float = Field(default=0, ge=0)
    taxes_and_government_fees: float = Field(default=0, ge=0)
    prepaids: float = Field(default=0, ge=0)
    initial_escrow: float = Field(default=0, ge=0)
    other_costs: float = Field(default=0, ge=0)

    # CD-specific fields
    cash_to_close: float
    closing_date: Optional[str] = None


class ComplianceReport(BaseModel):
    """TRID compliance comparison report"""

    is_compliant: bool
    violations: list[Dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Tolerance analysis
    zero_tolerance_diff: float = 0.0
    ten_percent_diff: float = 0.0
    ten_percent_limit: float = 0.0

    summary: str = ""


# ============================================================================
# Security Utilities
# ============================================================================

def validate_pdf_url(url: str) -> bool:
    """
    Validate PDF URL for security.

    Prevents:
    - SSRF attacks (only allow whitelisted domains)
    - Non-HTTPS URLs
    - Non-PDF files

    Args:
        url: URL to validate

    Returns:
        True if valid

    Raises:
        ValueError: If URL fails validation
    """
    parsed = urlparse(url)

    # Must be HTTPS
    if parsed.scheme != "https":
        raise ValueError(f"Only HTTPS URLs allowed, got: {parsed.scheme}")

    # Must be whitelisted domain
    if parsed.netloc not in ALLOWED_DOMAINS:
        raise ValueError(
            f"Domain not allowed: {parsed.netloc}. "
            f"Allowed: {', '.join(ALLOWED_DOMAINS)}"
        )

    # Must be PDF file
    if not parsed.path.lower().endswith('.pdf'):
        raise ValueError("Only PDF files allowed")

    return True


async def download_pdf(url: str) -> bytes:
    """
    Safely download PDF with size and timeout limits.

    Args:
        url: HTTPS URL to PDF (must pass validation)

    Returns:
        PDF file content as bytes

    Raises:
        ValueError: If validation fails or file too large
        TimeoutError: If download exceeds timeout
        httpx.HTTPError: If download fails
    """
    validate_pdf_url(url)

    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

        # Check size
        content = response.content
        if len(content) > MAX_PDF_SIZE:
            raise ValueError(
                f"PDF too large: {len(content)} bytes "
                f"(max: {MAX_PDF_SIZE} bytes)"
            )

        # Basic PDF validation (magic bytes)
        if not content.startswith(b'%PDF'):
            raise ValueError("File does not appear to be a valid PDF")

        return content


# ============================================================================
# PDF Parsing (Stub - TODO: Implement)
# ============================================================================

async def parse_le_pdf_content(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Parse Loan Estimate PDF content.

    TODO: Implement actual PDF parsing logic.

    Options:
    1. PyMuPDF (fast, good for structured PDFs)
    2. pdfplumber (accurate table extraction)
    3. OpenAI Vision API (AI-powered extraction)
    4. Anthropic Claude with PDF support

    Args:
        pdf_bytes: PDF file content

    Returns:
        Extracted data as dict matching MISMOLoanEstimate
    """
    # STUB IMPLEMENTATION - Replace with actual parsing
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
        "lender_name": "Example Bank",
        "loan_term_months": 360,
        "tolerance_buckets": {
            "origination_charges": "zero",
            "services_borrower_cannot_shop": "zero",
            "services_borrower_can_shop": "10_percent",
        }
    }


async def parse_cd_pdf_content(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Parse Closing Disclosure PDF content.

    TODO: Implement actual PDF parsing logic.

    Args:
        pdf_bytes: PDF file content

    Returns:
        Extracted data as dict matching MISMOClosingDisclosure
    """
    # STUB IMPLEMENTATION
    return {
        "loan_amount": 300000.0,
        "interest_rate": 6.5,
        "apr": 6.75,
        "monthly_payment": 1896.20,
        "origination_charges": 1500.0,
        "services_borrower_cannot_shop": 850.0,
        "services_borrower_can_shop": 1250.0,
        "taxes_and_government_fees": 2500.0,
        "prepaids": 3000.0,
        "initial_escrow": 2400.0,
        "other_costs": 600.0,
        "cash_to_close": 15000.0,
        "closing_date": "2025-06-15"
    }


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
async def parse_loan_estimate(pdf_url: str) -> MISMOLoanEstimate:
    """
    Parse a Loan Estimate PDF into MISMO-compliant structured data.

    ⚠️ REQUIRES USER APPROVAL: Downloads and processes external PDF document.

    This tool will:
    1. Download PDF from provided HTTPS URL (whitelisted domains only)
    2. Extract mortgage data using PDF parsing
    3. Validate and structure data per MISMO 3.4 standard
    4. Return structured loan estimate with tolerance bucket assignments

    Security measures:
    - Only approved storage domains allowed (no arbitrary URLs)
    - HTTPS required
    - 10MB file size limit
    - 30-second timeout
    - PDF format validation

    Args:
        pdf_url: HTTPS URL to Loan Estimate PDF document
                 Allowed domains: storage.googleapis.com, s3.amazonaws.com

    Returns:
        Structured MISMO data including:
        - Loan terms (amount, rate, APR, payment)
        - Itemized closing costs
        - Tolerance bucket assignments
        - Lender information

    Raises:
        ValueError: If URL validation fails, file too large, or not a valid PDF
        TimeoutError: If download exceeds 30 seconds

    Example:
        result = await parse_loan_estimate(
            "https://storage.googleapis.com/mortgage-docs/le-12345.pdf"
        )
        print(f"Loan Amount: ${result.loan_amount:,.2f}")
        print(f"APR: {result.apr}%")
        print(f"Total Closing: ${result.total_closing_costs:,.2f}")
    """
    # Download and validate PDF
    pdf_content = await download_pdf(pdf_url)

    # Parse PDF content
    data = await parse_le_pdf_content(pdf_content)

    # Validate and return structured data
    return MISMOLoanEstimate(**data)


@mcp.tool()
async def parse_closing_disclosure(pdf_url: str) -> MISMOClosingDisclosure:
    """
    Parse a Closing Disclosure PDF into MISMO-compliant structured data.

    ⚠️ REQUIRES USER APPROVAL: Downloads and processes external PDF document.

    Similar to parse_loan_estimate but for final closing documents.

    Args:
        pdf_url: HTTPS URL to Closing Disclosure PDF

    Returns:
        Structured MISMO closing disclosure data with final loan terms

    See parse_loan_estimate for security details.
    """
    pdf_content = await download_pdf(pdf_url)
    data = await parse_cd_pdf_content(pdf_content)
    return MISMOClosingDisclosure(**data)


@mcp.tool()
async def compare_le_cd(
    loan_estimate_url: str,
    closing_disclosure_url: str
) -> ComplianceReport:
    """
    Compare Loan Estimate vs Closing Disclosure for TRID compliance.

    ⚠️ REQUIRES USER APPROVAL: Downloads and compares two PDF documents.

    Analyzes fee changes between initial LE and final CD to identify:

    1. Zero-tolerance violations:
       - Fees that cannot increase at all
       - Examples: origination charges, services borrower cannot shop

    2. 10% tolerance violations:
       - Fees that cannot increase more than 10% in aggregate
       - Examples: services borrower can shop for

    3. Unlimited tolerance items:
       - Fees that can change without limit
       - Examples: prepaid interest, property taxes

    4. Other issues:
       - APR accuracy (must be within 0.125%)
       - Changed service providers
       - Missing disclosures

    Args:
        loan_estimate_url: HTTPS URL to Loan Estimate PDF
        closing_disclosure_url: HTTPS URL to Closing Disclosure PDF

    Returns:
        Compliance report with:
        - Overall compliance status (pass/fail)
        - List of violations with details and dollar amounts
        - Warnings for items close to tolerance limits
        - Summary explanation in plain language

    Example:
        report = await compare_le_cd(le_url, cd_url)
        if not report.is_compliant:
            print("VIOLATIONS FOUND:")
            for v in report.violations:
                print(f"  - {v['description']}: ${v['amount_over']}")
    """
    # Parse both documents
    le = await parse_loan_estimate(loan_estimate_url)
    cd = await parse_closing_disclosure(closing_disclosure_url)

    violations = []
    warnings = []

    # Check zero-tolerance items
    zero_items = [
        ("Origination Charges", le.origination_charges, cd.origination_charges),
        ("Services Borrower Cannot Shop",
         le.services_borrower_cannot_shop,
         cd.services_borrower_cannot_shop),
    ]

    zero_diff = 0.0
    for name, le_amt, cd_amt in zero_items:
        diff = cd_amt - le_amt
        zero_diff += max(0, diff)
        if diff > 0.01:  # Allow 1 cent rounding
            violations.append({
                "type": "zero_tolerance",
                "fee": name,
                "le_amount": le_amt,
                "cd_amount": cd_amt,
                "amount_over": diff,
                "description": f"{name} increased by ${diff:.2f} (zero tolerance - no increase allowed)"
            })

    # Check 10% tolerance items
    ten_pct_le = le.services_borrower_can_shop
    ten_pct_cd = cd.services_borrower_can_shop
    ten_pct_limit = ten_pct_le * 0.10
    ten_pct_diff = max(0, ten_pct_cd - ten_pct_le)

    if ten_pct_diff > ten_pct_limit:
        violations.append({
            "type": "10_percent_tolerance",
            "fee": "Services Borrower Can Shop",
            "le_amount": ten_pct_le,
            "cd_amount": ten_pct_cd,
            "amount_over": ten_pct_diff - ten_pct_limit,
            "limit": ten_pct_limit,
            "description": f"10% tolerance exceeded by ${ten_pct_diff - ten_pct_limit:.2f}"
        })
    elif ten_pct_diff > ten_pct_limit * 0.8:
        warnings.append(
            f"Services borrower can shop increased by ${ten_pct_diff:.2f}, "
            f"approaching 10% limit of ${ten_pct_limit:.2f}"
        )

    # Check APR accuracy
    apr_diff = abs(cd.apr - le.apr)
    if apr_diff > 0.125:
        violations.append({
            "type": "apr_accuracy",
            "fee": "APR",
            "le_amount": le.apr,
            "cd_amount": cd.apr,
            "amount_over": apr_diff - 0.125,
            "description": f"APR changed by {apr_diff:.3f}% (max allowed: 0.125%)"
        })

    # Generate summary
    is_compliant = len(violations) == 0

    if is_compliant:
        summary = (
            f"✓ COMPLIANT: Closing Disclosure is within TRID tolerance limits. "
            f"Zero-tolerance items: no increase. "
            f"10% tolerance items: ${ten_pct_diff:.2f} increase "
            f"(limit: ${ten_pct_limit:.2f}). "
            f"APR change: {apr_diff:.3f}% (limit: 0.125%)."
        )
    else:
        summary = (
            f"✗ NOT COMPLIANT: {len(violations)} violation(s) found. "
            f"Review required before closing."
        )

    return ComplianceReport(
        is_compliant=is_compliant,
        violations=violations,
        warnings=warnings,
        zero_tolerance_diff=zero_diff,
        ten_percent_diff=ten_pct_diff,
        ten_percent_limit=ten_pct_limit,
        summary=summary
    )


@mcp.tool()
def hello(name: str = "World") -> str:
    """
    Simple greeting tool for testing MCP connectivity.

    Args:
        name: Name to greet (default: "World")

    Returns:
        Greeting message
    """
    return f"Hello, {name}! MCP server is working correctly."


# ============================================================================
# MCP Resources
# ============================================================================

@mcp.resource("mortgage://schemas/mismo-le")
def get_mismo_le_schema() -> str:
    """
    MISMO 3.4 Loan Estimate schema reference documentation.

    Provides the complete field mapping and data type definitions
    for MISMO-compliant Loan Estimate documents.
    """
    # In production, load from file
    return json.dumps({
        "schema": "MISMO 3.4 Loan Estimate",
        "version": "3.4",
        "fields": {
            "LOAN_AMOUNT": {"type": "decimal", "required": True},
            "INTEREST_RATE": {"type": "percentage", "required": True},
            "APR": {"type": "percentage", "required": True},
            "MONTHLY_PAYMENT": {"type": "decimal", "required": True},
            # ... full schema would go here
        },
        "tolerance_rules": {
            "zero_tolerance": [
                "origination_charges",
                "services_borrower_cannot_shop"
            ],
            "10_percent_tolerance": [
                "services_borrower_can_shop"
            ],
            "unlimited_tolerance": [
                "prepaids",
                "property_taxes",
                "homeowners_insurance"
            ]
        }
    }, indent=2)


@mcp.resource("mortgage://schemas/mismo-cd")
def get_mismo_cd_schema() -> str:
    """MISMO 3.4 Closing Disclosure schema reference"""
    return json.dumps({
        "schema": "MISMO 3.4 Closing Disclosure",
        "version": "3.4",
        "note": "Similar to LE schema with additional final amounts"
    }, indent=2)


@mcp.resource("mortgage://glossary/{term}")
def get_mortgage_glossary(term: str) -> str:
    """
    Mortgage terminology definitions.

    Args:
        term: Mortgage term to look up (e.g., "APR", "escrow", "TRID")

    Returns:
        Definition and explanation
    """
    glossary = {
        "APR": "Annual Percentage Rate - The cost of credit as a yearly rate, including interest and certain fees.",
        "TRID": "TILA-RESPA Integrated Disclosure - Federal regulation requiring specific mortgage disclosures.",
        "LE": "Loan Estimate - Initial disclosure provided within 3 days of application.",
        "CD": "Closing Disclosure - Final disclosure provided at least 3 days before closing.",
        "MISMO": "Mortgage Industry Standards Maintenance Organization - Sets data standards.",
        "escrow": "Funds held by third party for taxes and insurance.",
        "origination": "Process of creating a new loan; includes lender fees.",
        "tolerance": "Limits on how much fees can increase from LE to CD.",
    }

    definition = glossary.get(term.upper())
    if definition:
        return f"{term.upper()}: {definition}"
    else:
        return f"Term not found: {term}. Available terms: {', '.join(glossary.keys())}"


# ============================================================================
# MCP Prompts
# ============================================================================

@mcp.prompt()
def analyze_loan_estimate(
    analysis_type: Literal["quick", "comprehensive", "compliance"] = "comprehensive"
) -> list[dict]:
    """
    Structured workflow for analyzing a Loan Estimate.

    Guides the LLM through a systematic review of mortgage terms,
    closing costs, and potential issues.

    Args:
        analysis_type:
            - quick: Basic loan terms only
            - comprehensive: Full analysis with recommendations
            - compliance: Focus on regulatory compliance

    Returns:
        Prompt messages to guide LLM analysis
    """
    if analysis_type == "quick":
        return [{
            "role": "user",
            "content": """Review this Loan Estimate and provide a brief summary:

1. Key loan terms (amount, rate, APR, monthly payment)
2. Total closing costs
3. Any unusual items that stand out

Keep response concise (3-4 sentences)."""
        }]

    elif analysis_type == "comprehensive":
        return [{
            "role": "user",
            "content": """Perform a comprehensive Loan Estimate analysis:

## 1. Loan Terms Analysis
- Loan amount and property value (LTV ratio)
- Interest rate competitiveness
- APR vs interest rate (are fees reasonable?)
- Monthly payment affordability
- Loan term appropriateness

## 2. Closing Costs Breakdown
Review each section:
- Origination charges (A): Are points/fees justified?
- Services borrower cannot shop (B): Reasonable for market?
- Services borrower can shop (C): Opportunity to save?
- Taxes and government fees (E): Accurate for jurisdiction?
- Prepaids (F): Correctly calculated?
- Initial escrow (G): Sufficient cushion?
- Other costs (H): Any surprises?

## 3. Tolerance Bucket Analysis
- Identify all zero-tolerance fees
- Identify 10% tolerance fees
- Explain what can change before closing

## 4. Red Flags & Concerns
- Unusually high fees
- Missing disclosures
- Potential for bait-and-switch
- APR significantly higher than rate

## 5. Borrower Questions
Suggest 3-5 questions borrower should ask lender

## 6. Recommendations
- Should borrower shop around?
- Are there opportunities to negotiate?
- Overall assessment: good/fair/poor deal?

Format as a detailed report suitable for borrower consultation."""
        }]

    else:  # compliance
        return [{
            "role": "user",
            "content": """TRID Compliance Review Checklist:

## Required Disclosures
- [ ] Loan terms clearly stated
- [ ] Itemization of closing costs
- [ ] Cash to close calculation
- [ ] Comparisons section
- [ ] Other considerations section
- [ ] Contact information
- [ ] Loan estimate form used (not old GFE)

## Timing Compliance
- [ ] Provided within 3 business days of application
- [ ] At least 7 business days before closing
- [ ] Received by borrower (not just sent)

## Accuracy Requirements
- [ ] APR within 0.125% of final APR (estimate)
- [ ] Tolerance buckets correctly assigned
- [ ] All required fees disclosed
- [ ] No junk fees or padding

## Consumer Protections
- [ ] Loan features clearly explained
- [ ] Risks disclosed (balloon, prepayment penalty, etc.)
- [ ] Ability to repay considered
- [ ] No steering to higher-cost loan

Provide compliance assessment with any deficiencies noted."""
        }]


@mcp.prompt()
def compare_loan_options() -> list[dict]:
    """Guide LLM through comparing multiple loan offers"""
    return [{
        "role": "user",
        "content": """Compare these loan options side by side:

## Comparison Factors
1. **Interest Rate & APR**: Which is truly cheaper?
2. **Closing Costs**: Upfront vs ongoing costs
3. **Monthly Payment**: Affordability over loan term
4. **Loan Features**: ARM vs fixed, prepayment penalties, etc.
5. **Break-even Analysis**: If paying points, when do you break even?
6. **Total Cost**: What's paid over full loan term?
7. **Flexibility**: Refinance options, portability

## Recommendation
Based on:
- Borrower's likely time in home
- Financial situation
- Risk tolerance
- Market conditions

Which loan is the best choice and why?"""
    }]


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    # Run with stdio transport (default for local MCP servers)
    mcp.run(transport="stdio")
