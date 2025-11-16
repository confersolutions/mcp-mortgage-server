from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import json
import os
from tools.parse_le_to_mismo import parse_le_to_mismo
from tools.parse_cd_to_mismo import parse_cd_to_mismo

app = FastAPI(
    title="MCP Mortgage Server",
    description="MCP server for parsing mortgage documents into MISMO format",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load MCP config
with open("mcp_config.json") as f:
    MCP_CONFIG = json.load(f)

class ToolRequest(BaseModel):
    tool: str
    input: Dict[str, Any]

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/tools")
async def list_tools():
    return {"tools": MCP_CONFIG["tools"]}

@app.post("/call")
async def call_tool(request: ToolRequest):
    tool_name = request.tool
    input_data = request.input

    # Validate tool exists
    tool_config = next((t for t in MCP_CONFIG["tools"] if t["name"] == tool_name), None)
    if not tool_config:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

    try:
        if tool_name == "hello":
            name = input_data.get("name", "World")
            return {"output": f"Hello, {name}!"}
        elif tool_name == "parse_le_to_mismo_json":
            return {"output": parse_le_to_mismo(input_data)}
        elif tool_name == "parse_cd_to_mismo_json":
            return {"output": parse_cd_to_mismo(input_data)}
        else:
            raise HTTPException(status_code=400, detail="Unknown tool")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
