# MCP Mortgage Server

**A Model Context Protocol (MCP) server for parsing and analyzing mortgage documents (Loan Estimates & Closing Disclosures) using MISMO standards.**

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/confersolutions/mcp-mortgage-server/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-2025--03--26-green.svg)](https://modelcontextprotocol.io)
[![Website](https://img.shields.io/badge/Website-confersolutions.ai-blue)](https://confersolutions.ai)

---

## 🎯 What is This?

This is a **Model Context Protocol (MCP) server** that allows AI assistants (like Claude Desktop, OpenAI Agents, etc.) to parse and analyze mortgage documents. It converts Loan Estimates (LE) and Closing Disclosures (CD) into structured MISMO-compliant JSON, and checks for TRID compliance violations.

### Key Features

✅ **MCP-Compliant** - Works natively with Claude Desktop, OpenAI Agents SDK, and other MCP clients
✅ **Secure** - URL validation, SSRF prevention, file size limits, timeout protection
✅ **Type-Safe** - Pydantic models ensure data validation
✅ **TRID Compliance** - Automated tolerance checking (zero-tolerance, 10% tolerance)
✅ **Resources** - Access to MISMO schemas and mortgage glossary
✅ **Prompts** - Pre-built workflows for loan analysis

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Claude Desktop (recommended) or another MCP-compatible client

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/confersolutions/mcp-mortgage-server.git
   cd mcp-mortgage-server
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Test the server**:
   ```bash
   python test_server.py
   ```

   You should see:
   ```
   ✓ All tests passed!
   Server is ready for MCP client connections!
   ```

### Usage with Claude Desktop

1. **Locate your Claude Desktop config file**:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. **Add this server**:
   ```json
   {
     "mcpServers": {
       "mortgage": {
         "command": "python",
         "args": ["/full/path/to/mcp-mortgage-server/server.py"]
       }
     }
   }
   ```

3. **Restart Claude Desktop**

4. **Use it in Claude**:
   ```
   Can you parse this loan estimate and summarize the key terms?
   URL: https://storage.googleapis.com/mortgage-docs/sample-le.pdf
   ```

   Claude will automatically call the appropriate MCP tool and parse the document.

---

## 🛠️ Available Tools

### 1. `hello`
Simple connectivity test.

```
Input: { "name": "World" }
Output: "Hello, World! MCP server is working correctly."
```

### 2. `parse_loan_estimate`
Parse a Loan Estimate PDF into MISMO-compliant JSON.

**Input**:
```json
{
  "pdf_url": "https://storage.googleapis.com/mortgage-docs/le-12345.pdf"
}
```

**Output**:
```json
{
  "loan_amount": 300000.0,
  "interest_rate": 6.5,
  "apr": 6.73,
  "monthly_payment": 1896.20,
  "total_closing_costs": 12000.00,
  "origination_charges": 1500.00,
  ...
}
```

**Security**: Only HTTPS URLs from whitelisted domains. 10MB size limit, 30s timeout.

### 3. `parse_closing_disclosure`
Parse a Closing Disclosure PDF into MISMO-compliant JSON.

Similar to `parse_loan_estimate` but for final closing documents.

### 4. `compare_le_cd`
Compare Loan Estimate vs Closing Disclosure for TRID compliance.

**Input**:
```json
{
  "loan_estimate_url": "https://storage.googleapis.com/docs/le.pdf",
  "closing_disclosure_url": "https://storage.googleapis.com/docs/cd.pdf"
}
```

**Output**:
```json
{
  "is_compliant": false,
  "violations": [
    {
      "type": "zero_tolerance",
      "fee": "Origination Charges",
      "le_amount": 1500.00,
      "cd_amount": 1600.00,
      "amount_over": 100.00,
      "description": "Origination Charges increased by $100.00"
    }
  ],
  "summary": "✗ NOT COMPLIANT: 1 violation(s) found"
}
```

---

## 📚 Resources

The server provides read-only resources:

- `mortgage://schemas/mismo-le` - MISMO 3.4 Loan Estimate schema
- `mortgage://schemas/mismo-cd` - MISMO 3.4 Closing Disclosure schema
- `mortgage://glossary/terms` - Mortgage terminology definitions

---

## 💡 Prompts

Pre-built workflows:

### `analyze_loan_estimate`

**Arguments**: `{ "analysis_type": "comprehensive" }`

**Types**: `quick`, `comprehensive`, `compliance`

---

## 🔒 Security

### Built-in Protections

- ✅ **HTTPS only** - HTTP URLs are rejected
- ✅ **Domain whitelist** - Only approved storage domains (prevents SSRF attacks)
- ✅ **File size limits** - 10MB maximum
- ✅ **Timeout protection** - 30-second download timeout
- ✅ **PDF validation** - Checks magic bytes
- ✅ **Type safety** - All inputs/outputs validated with Pydantic

### Allowed Domains

By default:
- `storage.googleapis.com`
- `s3.amazonaws.com`
- `mortgage-docs.confer.ai`

To add more, set `ALLOWED_DOMAINS` environment variable.

---

## 🧪 Development

### Run Tests

```bash
# Quick test suite
python test_server.py

# Full pytest suite
pytest tests/ -v
```

### Test with MCP Inspector

```bash
npm install -g @modelcontextprotocol/inspector
npx @modelcontextprotocol/inspector python server.py
```

---

## 📈 Roadmap

### ✅ v2.0.0 (Current)
- Modern MCP protocol implementation
- Basic tool definitions with stub data
- Security controls
- Resources and prompts
- Type-safe data models

### 🚧 v2.1.0 (In Progress)
- Real PDF parsing (AI-powered or PyMuPDF)
- Comprehensive test suite
- Performance optimizations

### 🔮 v2.2.0 (Planned)
- Streaming support
- Progress notifications
- Background task queue
- Additional mortgage analysis tools

---

## 🔄 Migrating from v0.1.0

If upgrading from the old REST API version:
- See **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Step-by-step instructions
- See **[MODERNIZATION_SUMMARY.md](MODERNIZATION_SUMMARY.md)** - Analysis of changes

**Key Changes**:
- ❌ Removed FastAPI/HTTP REST API
- ✅ Added MCP protocol (JSON-RPC 2.0 via stdio)
- ✅ Removed API key authentication
- ✅ Added type-safe tool definitions
- ✅ Added resources and prompts

---

## 📖 Documentation

- **[MCP Specification](https://modelcontextprotocol.io/specification/2025-03-26)** - Official protocol spec
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Detailed migration instructions
- **[MODERNIZATION_SUMMARY.md](MODERNIZATION_SUMMARY.md)** - Modernization analysis

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🏢 About

Maintained by [Confer Solutions](https://confersolutions.ai)

**Contact**: info@confersolutions.ai

---

## ⭐ Changelog

### v2.0.0 (2025-11-16) - Modern MCP Protocol

**Major Rewrite**: Complete architectural modernization to MCP specification 2025-03-26.

**Added**:
- MCP protocol support (JSON-RPC 2.0 via stdio)
- Four tools: hello, parse_loan_estimate, parse_closing_disclosure, compare_le_cd
- Resources: MISMO schemas, mortgage glossary
- Prompts: analyze_loan_estimate
- Security: URL validation, SSRF prevention, size limits
- Type safety: Pydantic models

**Removed**:
- FastAPI/HTTP REST API
- API key authentication
- Rate limiting
- Static JSON configuration

**Changed**:
- Server: FastAPI → Official MCP SDK
- Transport: HTTP → stdio
- Dependencies: 15+ → 6 core packages

### v0.1.0 (2024-04-12) - Initial Release

**Deprecated**: REST API version. Use v2.0.0+.

---

**Status**: ✅ Active Development | 🏗️ Beta | 📦 Production-Ready Core

**Last Updated**: November 16, 2025
