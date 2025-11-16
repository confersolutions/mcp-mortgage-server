#!/usr/bin/env python3
"""
Modern MCP Server for Mortgage Document Processing
==================================================

Compliant with Model Context Protocol specification 2025-03-26.
Uses the official Anthropic MCP Python SDK.

Features:
- JSON-RPC 2.0 protocol via stdio transport
- Type-safe tools with Pydantic validation
- Resources for MISMO schemas
- Prompts for mortgage analysis workflows
- Security controls (URL validation, size limits)

Usage:
    # Run server
    python server.py

    # Use with Claude Desktop
    Add to claude_desktop_config.json:
    {
      "mcpServers": {
        "mortgage": {
          "command": "python",
          "args": ["/path/to/server.py"]
        }
      }
    }

Copyright (c) 2025 Confer Solutions
License: MIT
"""

import asyncio
import json
import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, field_validator

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Prompt,
    PromptMessage,
    GetPromptResult,
)

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
# Data Models (Pydantic)
# ============================================================================

class MISMOLoanEstimate(BaseModel):
    """MISMO-compliant Loan Estimate data structure"""

    # Loan Information
    loan_amount: float = Field(..., gt=0, lt=100_000_000, description="Total loan amount in USD")
    interest_rate: float = Field(..., ge=0, le=100, description="Interest rate as percentage")
    apr: float = Field(..., ge=0, le=100, description="Annual Percentage Rate")
    monthly_payment: float = Field(..., gt=0, description="Monthly principal and interest payment")

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
    tolerance_buckets: Dict[str, str] = Field(default_factory=dict)

    @field_validator('loan_amount')
    @classmethod
    def validate_reasonable_loan(cls, v):
        if v < 1000:
            raise ValueError("Loan amount too small (< $1,000)")
        return v

    @property
    def total_closing_costs(self) -> float:
        return sum([
            self.origination_charges,
            self.services_borrower_cannot_shop,
            self.services_borrower_can_shop,
            self.taxes_and_government_fees,
            self.prepaids,
            self.initial_escrow,
            self.other_costs
        ])


class MISMOClosingDisclosure(BaseModel):
    """MISMO-compliant Closing Disclosure data structure"""
    loan_amount: float = Field(..., gt=0)
    interest_rate: float = Field(..., ge=0, le=100)
    apr: float = Field(..., ge=0, le=100)
    monthly_payment: float = Field(..., gt=0)
    origination_charges: float = Field(default=0, ge=0)
    services_borrower_cannot_shop: float = Field(default=0, ge=0)
    services_borrower_can_shop: float = Field(default=0, ge=0)
    taxes_and_government_fees: float = Field(default=0, ge=0)
    prepaids: float = Field(default=0, ge=0)
    initial_escrow: float = Field(default=0, ge=0)
    other_costs: float = Field(default=0, ge=0)
    cash_to_close: float
    closing_date: Optional[str] = None


class ComplianceReport(BaseModel):
    """TRID compliance comparison report"""
    is_compliant: bool
    violations: list[Dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    zero_tolerance_diff: float = 0.0
    ten_percent_diff: float = 0.0
    ten_percent_limit: float = 0.0
    summary: str = ""


# ============================================================================
# Security Utilities
# ============================================================================

def validate_pdf_url(url: str) -> bool:
    """Validate PDF URL for security (prevents SSRF attacks)"""
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise ValueError(f"Only HTTPS URLs allowed, got: {parsed.scheme}")

    if parsed.netloc not in ALLOWED_DOMAINS:
        raise ValueError(
            f"Domain not allowed: {parsed.netloc}. "
            f"Allowed: {', '.join(ALLOWED_DOMAINS)}"
        )

    if not parsed.path.lower().endswith('.pdf'):
        raise ValueError("Only PDF files allowed")

    return True


async def download_pdf(url: str) -> bytes:
    """Safely download PDF with size and timeout limits"""
    validate_pdf_url(url)

    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

        content = response.content
        if len(content) > MAX_PDF_SIZE:
            raise ValueError(f"PDF too large: {len(content)} bytes (max: {MAX_PDF_SIZE})")

        if not content.startswith(b'%PDF'):
            raise ValueError("File does not appear to be a valid PDF")

        return content


# ============================================================================
# PDF Parsing (Stub - TODO: Implement with PyMuPDF or AI)
# ============================================================================

async def parse_le_pdf_content(pdf_bytes: bytes) -> Dict[str, Any]:
    """Parse Loan Estimate PDF content - STUB IMPLEMENTATION"""
    # TODO: Implement actual PDF parsing using:
    # Option 1: PyMuPDF for structured extraction
    # Option 2: Claude API for AI-powered extraction (recommended)
    # Option 3: OpenAI GPT-4 Vision API

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
    """Parse Closing Disclosure PDF content - STUB IMPLEMENTATION"""
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
# Tool Implementations
# ============================================================================

async def tool_parse_loan_estimate(arguments: dict) -> list[TextContent]:
    """Parse a Loan Estimate PDF into MISMO-compliant structured data"""
    pdf_url = arguments.get("pdf_url")
    if not pdf_url:
        raise ValueError("pdf_url is required")

    # Download and validate PDF
    pdf_content = await download_pdf(pdf_url)

    # Parse PDF content
    data = await parse_le_pdf_content(pdf_content)

    # Validate and return structured data
    le = MISMOLoanEstimate(**data)

    return [TextContent(
        type="text",
        text=json.dumps({
            "loan_amount": le.loan_amount,
            "interest_rate": le.interest_rate,
            "apr": le.apr,
            "monthly_payment": le.monthly_payment,
            "total_closing_costs": le.total_closing_costs,
            "origination_charges": le.origination_charges,
            "services_borrower_cannot_shop": le.services_borrower_cannot_shop,
            "services_borrower_can_shop": le.services_borrower_can_shop,
            "taxes_and_government_fees": le.taxes_and_government_fees,
            "prepaids": le.prepaids,
            "initial_escrow": le.initial_escrow,
            "other_costs": le.other_costs,
            "lender_name": le.lender_name,
            "loan_term_months": le.loan_term_months,
            "tolerance_buckets": le.tolerance_buckets
        }, indent=2)
    )]


async def tool_parse_closing_disclosure(arguments: dict) -> list[TextContent]:
    """Parse a Closing Disclosure PDF into MISMO-compliant structured data"""
    pdf_url = arguments.get("pdf_url")
    if not pdf_url:
        raise ValueError("pdf_url is required")

    pdf_content = await download_pdf(pdf_url)
    data = await parse_cd_pdf_content(pdf_content)
    cd = MISMOClosingDisclosure(**data)

    return [TextContent(
        type="text",
        text=json.dumps(cd.dict(), indent=2)
    )]


async def tool_compare_le_cd(arguments: dict) -> list[TextContent]:
    """Compare Loan Estimate vs Closing Disclosure for TRID compliance"""
    le_url = arguments.get("loan_estimate_url")
    cd_url = arguments.get("closing_disclosure_url")

    if not le_url or not cd_url:
        raise ValueError("Both loan_estimate_url and closing_disclosure_url are required")

    # Parse both documents
    le_content = await download_pdf(le_url)
    cd_content = await download_pdf(cd_url)

    le_data = await parse_le_pdf_content(le_content)
    cd_data = await parse_cd_pdf_content(cd_content)

    le = MISMOLoanEstimate(**le_data)
    cd = MISMOClosingDisclosure(**cd_data)

    # Perform compliance checks
    violations = []
    warnings = []

    # Check zero-tolerance items
    zero_items = [
        ("Origination Charges", le.origination_charges, cd.origination_charges),
        ("Services Borrower Cannot Shop", le.services_borrower_cannot_shop, cd.services_borrower_cannot_shop),
    ]

    zero_diff = 0.0
    for name, le_amt, cd_amt in zero_items:
        diff = cd_amt - le_amt
        zero_diff += max(0, diff)
        if diff > 0.01:
            violations.append({
                "type": "zero_tolerance",
                "fee": name,
                "le_amount": le_amt,
                "cd_amount": cd_amt,
                "amount_over": diff,
                "description": f"{name} increased by ${diff:.2f} (zero tolerance)"
            })

    # Check 10% tolerance
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

    # Check APR accuracy
    apr_diff = abs(cd.apr - le.apr)
    if apr_diff > 0.125:
        violations.append({
            "type": "apr_accuracy",
            "le_apr": le.apr,
            "cd_apr": cd.apr,
            "difference": apr_diff,
            "description": f"APR changed by {apr_diff:.3f}% (max allowed: 0.125%)"
        })

    is_compliant = len(violations) == 0
    summary = "✓ COMPLIANT" if is_compliant else f"✗ NOT COMPLIANT: {len(violations)} violation(s)"

    report = ComplianceReport(
        is_compliant=is_compliant,
        violations=violations,
        warnings=warnings,
        zero_tolerance_diff=zero_diff,
        ten_percent_diff=ten_pct_diff,
        ten_percent_limit=ten_pct_limit,
        summary=summary
    )

    return [TextContent(
        type="text",
        text=json.dumps(report.dict(), indent=2)
    )]


async def tool_hello(arguments: dict) -> list[TextContent]:
    """Simple greeting tool for testing MCP connectivity"""
    name = arguments.get("name", "World")
    return [TextContent(
        type="text",
        text=f"Hello, {name}! MCP server is working correctly."
    )]


# ============================================================================
# MCP Server Setup
# ============================================================================

async def main():
    """Main server entry point"""
    server = Server("mortgage-document-parser")

    # Register tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="hello",
                description="Simple greeting tool for testing MCP connectivity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name to greet (default: World)"
                        }
                    }
                }
            ),
            Tool(
                name="parse_loan_estimate",
                description=(
                    "Parse a Loan Estimate PDF into MISMO-compliant structured data. "
                    "⚠️ REQUIRES APPROVAL: Downloads external PDF document. "
                    "Security: Only approved domains allowed, 10MB limit, 30s timeout."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pdf_url": {
                            "type": "string",
                            "description": "HTTPS URL to Loan Estimate PDF (allowed domains: storage.googleapis.com, s3.amazonaws.com)"
                        }
                    },
                    "required": ["pdf_url"]
                }
            ),
            Tool(
                name="parse_closing_disclosure",
                description=(
                    "Parse a Closing Disclosure PDF into MISMO-compliant structured data. "
                    "⚠️ REQUIRES APPROVAL: Downloads external PDF document."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pdf_url": {
                            "type": "string",
                            "description": "HTTPS URL to Closing Disclosure PDF"
                        }
                    },
                    "required": ["pdf_url"]
                }
            ),
            Tool(
                name="compare_le_cd",
                description=(
                    "Compare Loan Estimate vs Closing Disclosure for TRID compliance. "
                    "⚠️ REQUIRES APPROVAL: Downloads and compares two PDF documents. "
                    "Checks for zero-tolerance, 10% tolerance, and APR violations."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loan_estimate_url": {
                            "type": "string",
                            "description": "HTTPS URL to Loan Estimate PDF"
                        },
                        "closing_disclosure_url": {
                            "type": "string",
                            "description": "HTTPS URL to Closing Disclosure PDF"
                        }
                    },
                    "required": ["loan_estimate_url", "closing_disclosure_url"]
                }
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls"""
        if name == "hello":
            return await tool_hello(arguments)
        elif name == "parse_loan_estimate":
            return await tool_parse_loan_estimate(arguments)
        elif name == "parse_closing_disclosure":
            return await tool_parse_closing_disclosure(arguments)
        elif name == "compare_le_cd":
            return await tool_compare_le_cd(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    # Register resources
    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="mortgage://schemas/mismo-le",
                name="MISMO Loan Estimate Schema",
                mimeType="application/json",
                description="MISMO 3.4 Loan Estimate schema reference"
            ),
            Resource(
                uri="mortgage://schemas/mismo-cd",
                name="MISMO Closing Disclosure Schema",
                mimeType="application/json",
                description="MISMO 3.4 Closing Disclosure schema reference"
            ),
            Resource(
                uri="mortgage://glossary/terms",
                name="Mortgage Glossary",
                mimeType="application/json",
                description="Mortgage terminology definitions"
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """Read resource content"""
        if uri == "mortgage://schemas/mismo-le":
            return json.dumps({
                "schema": "MISMO 3.4 Loan Estimate",
                "version": "3.4",
                "tolerance_rules": {
                    "zero_tolerance": ["origination_charges", "services_borrower_cannot_shop"],
                    "10_percent_tolerance": ["services_borrower_can_shop"],
                    "unlimited_tolerance": ["prepaids", "property_taxes", "homeowners_insurance"]
                }
            }, indent=2)
        elif uri == "mortgage://schemas/mismo-cd":
            return json.dumps({
                "schema": "MISMO 3.4 Closing Disclosure",
                "version": "3.4"
            }, indent=2)
        elif uri == "mortgage://glossary/terms":
            return json.dumps({
                "APR": "Annual Percentage Rate - The cost of credit as a yearly rate",
                "TRID": "TILA-RESPA Integrated Disclosure",
                "LE": "Loan Estimate",
                "CD": "Closing Disclosure",
                "MISMO": "Mortgage Industry Standards Maintenance Organization"
            }, indent=2)
        else:
            raise ValueError(f"Unknown resource: {uri}")

    # Register prompts
    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="analyze_loan_estimate",
                description="Structured workflow for analyzing a Loan Estimate",
                arguments=[
                    {
                        "name": "analysis_type",
                        "description": "Type of analysis: quick, comprehensive, or compliance",
                        "required": False
                    }
                ]
            ),
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict) -> GetPromptResult:
        """Get prompt content"""
        if name == "analyze_loan_estimate":
            analysis_type = arguments.get("analysis_type", "comprehensive")

            if analysis_type == "comprehensive":
                return GetPromptResult(
                    description="Comprehensive Loan Estimate analysis",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text="""Perform a comprehensive Loan Estimate analysis:

## 1. Loan Terms Analysis
- Loan amount and LTV ratio
- Interest rate competitiveness
- APR vs interest rate
- Monthly payment affordability

## 2. Closing Costs Breakdown
Review each section and identify opportunities to save

## 3. Tolerance Bucket Analysis
Identify zero-tolerance and 10% tolerance fees

## 4. Red Flags & Concerns
Note any unusually high fees or missing disclosures

## 5. Recommendations
Should borrower shop around? Negotiate?"""
                            )
                        )
                    ]
                )
            else:
                return GetPromptResult(
                    description="Quick Loan Estimate review",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text="Provide a brief summary of key loan terms and total closing costs."
                            )
                        )
                    ]
                )

        raise ValueError(f"Unknown prompt: {name}")

    # Run server with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    asyncio.run(main())
