# Migration Guide: REST API → Modern MCP Server

## Overview

This guide walks through migrating from the current FastAPI REST server to a modern Model Context Protocol (MCP) server compliant with the 2025-03-26 specification.

**Timeline**: 2-4 weeks
**Effort**: 96-148 hours
**Risk**: Medium (requires architectural changes but well-documented)

---

## Before You Start

### Prerequisites

1. **Backup current code**:
   ```bash
   git tag v0.1.0-rest-api
   git checkout -b feature/mcp-modernization
   ```

2. **Install MCP SDK**:
   ```bash
   pip install fastmcp
   # OR
   pip install mcp
   ```

3. **Install MCP Inspector** (for testing):
   ```bash
   npm install -g @modelcontextprotocol/inspector
   ```

### Understanding the Change

**What's Changing:**
- Protocol: HTTP REST → JSON-RPC 2.0
- Transport: Network (port 8001) → stdio
- Authentication: API keys → None (local process)
- Framework: FastAPI → FastMCP SDK
- Configuration: Static JSON → Type-driven

**What's NOT Changing:**
- Business logic (mortgage parsing)
- Data models (MISMO format)
- Programming language (Python)
- Core functionality (same tools, better interface)

---

## Phase 1: Foundation (Week 1)

### Step 1.1: Update Dependencies

**File**: `requirements.txt`

**Remove**:
```txt
fastapi>=0.109.0
uvicorn>=0.27.0
slowapi>=0.1.9
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
aiohttp>=3.9.0
nest-asyncio>=1.6.0
crewai>=0.19.0
pyautogen>=0.7.5
langchain>=0.1.0
```

**Add**:
```txt
fastmcp>=2.0.0
httpx>=0.26.0
```

**Keep**:
```txt
pydantic>=2.0.0
python-dotenv>=1.0.0
PyMuPDF>=1.23.8
openai>=1.12.0
pytest>=7.4.0
pytest-asyncio>=0.21.1
```

**Command**:
```bash
pip install fastmcp httpx
pip uninstall -y fastapi uvicorn slowapi python-jose passlib aiohttp
```

### Step 1.2: Create Modern Server

**Option A: Start Fresh (Recommended)**

1. Copy the provided `server.modern.py` to your repo
2. Rename: `mv server.py server.old.py`
3. Rename: `mv server.modern.py server.py`
4. Test: `python server.py` (should start without errors)

**Option B: Gradual Migration**

1. Create `server_v2.py` alongside existing `server.py`
2. Implement one tool at a time
3. Test with MCP Inspector after each tool
4. Switch over when all tools working

### Step 1.3: Test Basic Connectivity

**Test with MCP Inspector**:
```bash
# Terminal 1: Run MCP Inspector
npx @modelcontextprotocol/inspector python server.py

# Should open web UI at http://localhost:5173
# You should see:
# - Server: "Mortgage Document Parser"
# - Tools: hello, parse_loan_estimate, parse_closing_disclosure, compare_le_cd
# - Resources: mortgage://schemas/mismo-le, etc.
# - Prompts: analyze_loan_estimate, compare_loan_options
```

**Test hello tool**:
1. In Inspector UI, select "hello" tool
2. Enter parameters: `{"name": "Test"}`
3. Click "Run"
4. Should see: `"Hello, Test! MCP server is working correctly."`

✅ **Success Criteria**: Hello tool returns correct response in Inspector

### Step 1.4: Update Configuration

**Delete**:
- `main.py` (duplicate server)
- `mcp_config.json` (static configuration)

**Create**:
- `claude_desktop_config.example.json` (user guidance)
- `.env.example` (environment variables)

**`.env.example`**:
```env
# Allowed PDF source domains (comma-separated)
ALLOWED_DOMAINS=storage.googleapis.com,s3.amazonaws.com

# Maximum PDF file size in bytes (default: 10MB)
MAX_PDF_SIZE=10485760

# Download timeout in seconds (default: 30)
DOWNLOAD_TIMEOUT=30
```

### Step 1.5: Update README

**Update** `README.md` to reflect MCP architecture:

```markdown
# MCP Mortgage Server

A Model Context Protocol (MCP) server for parsing and analyzing mortgage documents.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Add to Claude Desktop config:
   ```json
   {
     "mcpServers": {
       "mortgage": {
         "command": "python",
         "args": ["/path/to/server.py"]
       }
     }
   }
   ```

3. Restart Claude Desktop

4. Tools appear automatically in Claude interface

## Tools Available

- `parse_loan_estimate`: Parse LE PDF to MISMO JSON
- `parse_closing_disclosure`: Parse CD PDF to MISMO JSON
- `compare_le_cd`: Check TRID compliance
- `hello`: Test connectivity

## Resources Available

- `mortgage://schemas/mismo-le`: Schema reference
- `mortgage://glossary/{term}`: Terminology

## Development

Test with MCP Inspector:
```bash
npx @modelcontextprotocol/inspector python server.py
```
```

---

## Phase 2: Tool Implementation (Weeks 2-3)

### Step 2.1: Implement PDF Parsing

**Current**: All tools are stubs returning fake data

**Goal**: Implement real PDF parsing

**File**: `tools/parse_le_to_mismo.py`

**Options**:

**Option 1: PyMuPDF (Fast, works for structured PDFs)**
```python
import fitz  # PyMuPDF
from typing import Dict, Any

def extract_le_data(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extract data from LE PDF using PyMuPDF"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Strategy: Text extraction with positioning
    data = {}

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("dict")

        # Parse structured fields
        # Look for "Loan Amount" and extract value
        # Look for "Interest Rate" and extract value
        # etc.

    doc.close()
    return data
```

**Option 2: AI-Powered Extraction (Most Accurate)**
```python
import base64
from anthropic import Anthropic

async def extract_le_data(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extract data using Claude with PDF support"""
    client = Anthropic()

    # Convert PDF to base64
    pdf_base64 = base64.b64encode(pdf_bytes).decode()

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_base64
                    }
                },
                {
                    "type": "text",
                    "text": """Extract loan estimate data and return as JSON:
                    {
                      "loan_amount": <number>,
                      "interest_rate": <number>,
                      "apr": <number>,
                      "monthly_payment": <number>,
                      "origination_charges": <number>,
                      ...
                    }"""
                }
            ]
        }]
    )

    # Parse JSON from response
    import json
    return json.loads(response.content[0].text)
```

**Recommendation**: Start with Option 2 (AI-powered) for fastest results, optimize with Option 1 later if needed.

### Step 2.2: Add Validation

**Enhance** Pydantic models with validators:

```python
from pydantic import BaseModel, validator

class MISMOLoanEstimate(BaseModel):
    loan_amount: float
    interest_rate: float
    # ... other fields

    @validator('loan_amount')
    def validate_loan_amount(cls, v):
        if v <= 0:
            raise ValueError("Loan amount must be positive")
        if v > 50_000_000:
            raise ValueError("Loan amount unrealistic (> $50M)")
        return v

    @validator('interest_rate')
    def validate_interest_rate(cls, v):
        if v < 0 or v > 30:
            raise ValueError("Interest rate out of reasonable range")
        return v
```

### Step 2.3: Security Implementation

**Update** `download_pdf` with full security:

```python
async def download_pdf(url: str) -> bytes:
    """Safely download PDF with all security controls"""

    # 1. Validate URL
    validate_pdf_url(url)

    # 2. Download with timeout
    async with httpx.AsyncClient(
        timeout=DOWNLOAD_TIMEOUT,
        follow_redirects=False  # Prevent redirect attacks
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

        # 3. Check Content-Type
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower():
            raise ValueError(f"Expected PDF, got: {content_type}")

        # 4. Check size
        content = response.content
        if len(content) > MAX_PDF_SIZE:
            raise ValueError(f"PDF too large: {len(content)} bytes")

        # 5. Validate PDF magic bytes
        if not content.startswith(b'%PDF'):
            raise ValueError("Not a valid PDF file")

        # 6. Optional: Virus scan
        # if ENABLE_VIRUS_SCAN:
        #     scan_result = await scan_for_malware(content)
        #     if not scan_result.is_safe:
        #         raise ValueError("File failed security scan")

        return content
```

---

## Phase 3: Testing (Week 3)

### Step 3.1: Update Test Suite

**Delete**: Old REST API tests
**Create**: New MCP protocol tests

**File**: `tests/test_mcp_tools.py`

```python
import pytest
from server import (
    parse_loan_estimate,
    parse_closing_disclosure,
    compare_le_cd,
    hello
)

@pytest.mark.asyncio
async def test_hello_tool():
    """Test basic hello tool"""
    result = hello(name="Test")
    assert "Test" in result
    assert "MCP server is working" in result

@pytest.mark.asyncio
async def test_parse_le_security():
    """Test that parse_loan_estimate rejects invalid URLs"""

    # Should reject non-HTTPS
    with pytest.raises(ValueError, match="Only HTTPS"):
        await parse_loan_estimate("http://example.com/doc.pdf")

    # Should reject non-whitelisted domain
    with pytest.raises(ValueError, match="Domain not allowed"):
        await parse_loan_estimate("https://evil.com/doc.pdf")

    # Should reject non-PDF
    with pytest.raises(ValueError, match="Only PDF"):
        await parse_loan_estimate("https://storage.googleapis.com/file.txt")

@pytest.mark.asyncio
async def test_parse_le_valid(mock_pdf_response):
    """Test successful LE parsing"""
    url = "https://storage.googleapis.com/test/le.pdf"

    # Mock HTTP response
    with mock_pdf_response(url, "sample_le.pdf"):
        result = await parse_loan_estimate(url)

        assert result.loan_amount > 0
        assert 0 <= result.interest_rate <= 30
        assert result.apr >= result.interest_rate
        assert result.total_closing_costs > 0

@pytest.mark.asyncio
async def test_compare_le_cd_compliant():
    """Test TRID compliance check with compliant docs"""
    le_url = "https://storage.googleapis.com/test/le_good.pdf"
    cd_url = "https://storage.googleapis.com/test/cd_good.pdf"

    with mock_pdf_responses():
        report = await compare_le_cd(le_url, cd_url)

        assert report.is_compliant
        assert len(report.violations) == 0

@pytest.mark.asyncio
async def test_compare_le_cd_zero_tolerance_violation():
    """Test detection of zero-tolerance violations"""
    le_url = "https://storage.googleapis.com/test/le.pdf"
    cd_url = "https://storage.googleapis.com/test/cd_bad_zero.pdf"

    with mock_pdf_responses():
        report = await compare_le_cd(le_url, cd_url)

        assert not report.is_compliant
        assert any(v["type"] == "zero_tolerance" for v in report.violations)
```

### Step 3.2: Integration Testing

**Test with MCP Inspector**:

1. Start Inspector: `npx @modelcontextprotocol/inspector python server.py`
2. Test each tool with real PDFs
3. Verify error handling
4. Check resource access
5. Test prompts

**Test with Claude Desktop**:

1. Add server to config
2. Restart Claude Desktop
3. Chat: "Can you parse this loan estimate: [URL]"
4. Verify tool is called
5. Check results

### Step 3.3: Update CI/CD

**File**: `.github/workflows/ci.yml`

```yaml
name: CI/CD

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Type checking with mypy
      run: mypy server.py tools/ utils/

    - name: Lint with ruff
      run: ruff check .

    - name: Format check with black
      run: black --check .

    - name: Run tests
      run: pytest --cov=. --cov-report=xml -v

    - name: Test MCP server startup
      run: |
        # Test that server starts and responds
        timeout 5 python server.py || code=$?
        if [ $code -eq 124 ]; then
          echo "Server started successfully"
        else
          echo "Server failed to start"
          exit 1
        fi

    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
```

---

## Phase 4: Deployment & Documentation (Week 4)

### Step 4.1: Production Deployment

**MCP servers typically run locally** (stdio transport), but you can offer cloud deployment:

**Option 1: Stdio (Local) - Recommended**
- Users install on their machine
- No hosting costs
- Maximum privacy
- Configured in Claude Desktop

**Option 2: SSE (Cloud) - Advanced**
```python
# server.py
if __name__ == "__main__":
    import os
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "sse":
        # Server-Sent Events for cloud deployment
        mcp.run(transport="sse", port=8000)
    else:
        # Local stdio
        mcp.run(transport="stdio")
```

### Step 4.2: Create Examples

**File**: `examples/claude_desktop_usage.md`

```markdown
# Using with Claude Desktop

## Setup

1. **Locate config file**:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add server**:
   ```json
   {
     "mcpServers": {
       "mortgage": {
         "command": "python",
         "args": ["/full/path/to/server.py"]
       }
     }
   }
   ```

3. **Restart Claude Desktop**

## Usage Examples

### Parse a Loan Estimate
```
Can you parse this loan estimate and summarize the key terms?
URL: https://storage.googleapis.com/mortgage-docs/sample-le.pdf
```

### Compare LE vs CD
```
Please check if this closing disclosure is compliant with the loan estimate:
LE: https://storage.googleapis.com/docs/le-12345.pdf
CD: https://storage.googleapis.com/docs/cd-12345.pdf
```

### Use Analysis Prompt
```
Run a comprehensive analysis on this loan estimate:
https://storage.googleapis.com/docs/le-12345.pdf
```

Claude will automatically:
1. Call the appropriate MCP tool
2. Parse the PDF
3. Analyze the results
4. Provide detailed explanation
```

### Step 4.3: Update Documentation

**Create**: `docs/` directory with:

1. **`docs/architecture.md`**: MCP protocol overview
2. **`docs/security.md`**: Security controls and threat model
3. **`docs/tools.md`**: Tool reference documentation
4. **`docs/development.md`**: Developer guide
5. **`docs/troubleshooting.md`**: Common issues

**Update**: `README.md` with modern architecture

---

## Rollback Plan

If migration encounters issues:

### Emergency Rollback

```bash
# Restore old REST API server
git checkout v0.1.0-rest-api

# Or restore specific file
git checkout v0.1.0-rest-api -- server.py
```

### Gradual Rollback

Keep both servers running:
- `server.py` - New MCP server
- `server.old.py` - Old REST API
- Run old server: `python server.old.py`

---

## Success Checklist

Phase 1 Complete:
- [ ] FastMCP installed
- [ ] server.py converted to MCP
- [ ] Hello tool works in MCP Inspector
- [ ] main.py deleted
- [ ] mcp_config.json deleted
- [ ] README updated

Phase 2 Complete:
- [ ] parse_loan_estimate implemented
- [ ] parse_closing_disclosure implemented
- [ ] compare_le_cd implemented
- [ ] Security controls in place
- [ ] PDF parsing working
- [ ] Validation working

Phase 3 Complete:
- [ ] All tests passing
- [ ] Integration tests with Inspector
- [ ] Integration tests with Claude Desktop
- [ ] CI/CD updated
- [ ] >80% code coverage

Phase 4 Complete:
- [ ] Documentation complete
- [ ] Examples working
- [ ] Deployment guide written
- [ ] User guide written
- [ ] Tagged release (v2.0.0)

---

## Getting Help

### MCP Resources

- **Specification**: https://modelcontextprotocol.io/specification/2025-03-26
- **Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **FastMCP**: https://github.com/jlowin/fastmcp
- **Inspector**: https://github.com/modelcontextprotocol/inspector

### Common Issues

**Server won't start**:
- Check Python version (3.10+)
- Verify dependencies: `pip list | grep mcp`
- Check for syntax errors: `python -m py_compile server.py`

**Tools not appearing in Claude Desktop**:
- Verify config file location
- Check JSON syntax: `python -m json.tool < claude_desktop_config.json`
- Restart Claude Desktop completely
- Check logs: `~/Library/Logs/Claude/` (macOS)

**PDF parsing fails**:
- Verify URL is HTTPS
- Check domain is in ALLOWED_DOMAINS
- Test URL in browser (should download)
- Check PDF file size (< MAX_PDF_SIZE)

---

## Conclusion

This migration transforms your REST API into a modern MCP server that:

✅ Works natively with Claude Desktop, OpenAI Agents, and other MCP clients
✅ Has stronger security (no network exposure, better validation)
✅ Is easier to maintain (less code, type-driven)
✅ Follows 2025 best practices and standards
✅ Provides better LLM integration (resources, prompts)

**Next Steps**:
1. Start with Phase 1 (foundation)
2. Test thoroughly after each phase
3. Keep old code until confident
4. Deploy when all tests pass

Good luck with your migration!
