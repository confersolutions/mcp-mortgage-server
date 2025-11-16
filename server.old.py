"""
MCP (Mortgage Comparison Platform) Server
=======================================

A FastAPI-based server that provides mortgage document parsing and comparison tools.
Currently implements basic functionality with plans for full mortgage document parsing.

Features:
- API key authentication
- Rate limiting
- CORS support
- Framework integrations (CrewAI, AutoGen, LangChain)

Current Status:
- Version 0.1.0: Initial public release with "hello" tool for framework integration testing
- Future versions will include mortgage document parsing and comparison tools

For usage and documentation, see README.md

Website: https://confersolutions.ai
Repository: https://github.com/confersolutions/mcp-mortgage-server
Contact: info@confersolutions.ai

Copyright (c) 2024 Confer Solutions
License: MIT
Released: April 12, 2024
"""

from fastapi import FastAPI, Request, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Dict, Any, List
import json
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

# Version and metadata
__version__ = "0.1.0"  # Following semver: MAJOR.MINOR.PATCH
__author__ = "Confer Solutions"
__email__ = "info@confersolutions.ai"
__license__ = "MIT"
__copyright__ = "Copyright (c) 2024 Confer Solutions"
__status__ = "Beta"  # Changed to Beta for initial public release
__url__ = "https://github.com/confersolutions/mcp-mortgage-server"
__release_date__ = "2024-04-12"

# Load environment variables
load_dotenv()

# Security setup
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == os.getenv("API_KEY"):
        return api_key_header
    raise HTTPException(
        status_code=403,
        detail="Could not validate API key"
    )

# Rate limiting setup
RATE_LIMIT = os.getenv("RATE_LIMIT_PER_MINUTE", "120")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{RATE_LIMIT}/minute"]
)

app = FastAPI(
    title="MCP Server",
    description="Mortgage Comparison Platform API - Provides tools for parsing and comparing mortgage documents",
    version=__version__,
    docs_url="/docs",  # Enable Swagger UI
    redoc_url="/redoc"  # Enable ReDoc
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP tool configuration
MCP_CONFIG = {
    "tools": [
        {
            "name": "hello",
            "name_for_human": "Basic Hello Tool",
            "name_for_model": "hello",
            "description": "Basic tool for testing API connectivity and framework integration. More mortgage tools coming soon.",
            "parameters": {  # AutoGen format
                "type": "object",
                "properties": {
                    "name": { 
                        "type": "string",
                        "description": "Name to say hello to"
                    }
                },
                "required": []  # Optional parameter
            },
            "input_schema": {  # Keep for backward compatibility
                "type": "object",
                "properties": {
                    "name": { 
                        "type": "string",
                        "description": "Name to say hello to"
                    }
                }
            },
            "return_direct": True,
            "function": {  # LangChain format
                "name": "hello",
                "description": "Basic tool for testing API connectivity. Returns a hello message with optional name parameter.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": { 
                            "type": "string",
                            "description": "Name to say hello to"
                        }
                    }
                }
            }
        }
        # Additional mortgage tools will be added here
    ]
}

class ToolRequest(BaseModel):
    tool: str
    input: Dict[str, Any]

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__}
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/tools")
@limiter.limit(f"{RATE_LIMIT}/minute")
async def list_tools(
    request: Request,
    api_key: str = Depends(get_api_key)
):
    return {"tools": MCP_CONFIG["tools"]}

@app.post("/call")
@limiter.limit(f"{RATE_LIMIT}/minute")
async def call_tool(
    request: Request,
    tool_request: ToolRequest,
    api_key: str = Depends(get_api_key)
):
    tool_name = tool_request.tool
    input_data = tool_request.input

    # Validate tool exists
    tool_config = next((t for t in MCP_CONFIG["tools"] if t["name"] == tool_name), None)
    if not tool_config:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

    try:
        if tool_name == "hello":
            name = input_data.get("name", "World")
            return {"output": f"Hello, {name}!"}
        else:
            raise HTTPException(status_code=400, detail="Unknown tool")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8001)),
        workers=int(os.getenv("WORKERS", 1))
    ) 