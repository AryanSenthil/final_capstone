"""
Chat API Router for Damage Lab
==============================
Exposes the chat agent through REST API endpoints with streaming support.
"""

import json
import asyncio
from typing import Optional, AsyncGenerator
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI

from settings.constants import OPENAI_MODEL

# Import agent tools
from agent import (
    list_datasets,
    get_dataset_details,
    browse_directories,
    suggest_label,
    ingest_data,
    delete_dataset,
    generate_dataset_metadata,
    list_raw_folders,
    list_models,
    get_model_details,
    suggest_model_name,
    start_training,
    get_training_status,
    wait_for_training,
    delete_model,
    run_inference,
    list_tests,
    get_test_details,
    get_test_statistics,
    delete_test,
    get_workflow_guidance,
    compare_models,
    get_dataset_summary,
    get_training_recommendations,
    explain_results,
    list_reports,
    get_system_status,
    SYSTEM_INSTRUCTION,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Map of function names to actual functions
TOOL_FUNCTIONS = {
    "list_datasets": list_datasets,
    "get_dataset_details": get_dataset_details,
    "browse_directories": browse_directories,
    "suggest_label": suggest_label,
    "ingest_data": ingest_data,
    "delete_dataset": delete_dataset,
    "generate_dataset_metadata": generate_dataset_metadata,
    "list_raw_folders": list_raw_folders,
    "list_models": list_models,
    "get_model_details": get_model_details,
    "suggest_model_name": suggest_model_name,
    "start_training": start_training,
    "get_training_status": get_training_status,
    "wait_for_training": wait_for_training,
    "delete_model": delete_model,
    "run_inference": run_inference,
    "list_tests": list_tests,
    "get_test_details": get_test_details,
    "get_test_statistics": get_test_statistics,
    "delete_test": delete_test,
    "get_workflow_guidance": get_workflow_guidance,
    "compare_models": compare_models,
    "get_dataset_summary": get_dataset_summary,
    "get_training_recommendations": get_training_recommendations,
    "explain_results": explain_results,
    "list_reports": list_reports,
    "get_system_status": get_system_status,
}


# ============================================================================
# Tool Specification Builder
# ============================================================================

import inspect
from typing import Callable, Any


def python_type_to_json_schema(py_type: Any) -> dict:
    """Convert Python type annotation to JSON schema type."""
    type_str = str(py_type)

    if py_type is str or "str" in type_str:
        return {"type": "string"}
    elif py_type is int or "int" in type_str:
        return {"type": "integer"}
    elif py_type is float or "float" in type_str:
        return {"type": "number"}
    elif py_type is bool or "bool" in type_str:
        return {"type": "boolean"}
    elif py_type is list or "list" in type_str.lower():
        return {"type": "array", "items": {"type": "string"}}
    elif "Optional" in type_str:
        inner = type_str.replace("typing.Optional[", "").replace("Optional[", "").rstrip("]")
        if "str" in inner:
            return {"type": "string"}
        elif "int" in inner:
            return {"type": "integer"}
        elif "float" in inner:
            return {"type": "number"}
        elif "list" in inner.lower():
            return {"type": "array", "items": {"type": "string"}}
        return {"type": "string"}
    else:
        return {"type": "string"}


def function_to_tool_spec(func: Callable) -> dict:
    """Convert a Python function to OpenAI tool specification."""
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""

    # Parse docstring for parameter descriptions
    param_docs = {}
    in_args = False
    current_param = None

    for line in doc.split("\n"):
        line = line.strip()
        if line.startswith("Args:"):
            in_args = True
            continue
        elif line.startswith("Returns:"):
            break
        elif in_args and line:
            if ":" in line and not line.startswith("-"):
                parts = line.split(":", 1)
                current_param = parts[0].strip()
                param_docs[current_param] = parts[1].strip() if len(parts) > 1 else ""
            elif current_param and line:
                param_docs[current_param] += " " + line

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name in ["self", "cls"]:
            continue

        param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
        schema = python_type_to_json_schema(param_type)

        if param_name in param_docs:
            schema["description"] = param_docs[param_name]

        properties[param_name] = schema

        if param.default == inspect.Parameter.empty:
            if "Optional" not in str(param_type):
                required.append(param_name)

    description = doc.split("\n")[0] if doc else f"Call {func.__name__}"

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }


def build_tools_list() -> list[dict]:
    """Build the tools list for OpenAI API."""
    tools = []
    for name, func in TOOL_FUNCTIONS.items():
        if callable(func):
            try:
                tools.append(function_to_tool_spec(func))
            except Exception:
                pass
    return tools


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool function and return the result as a string."""
    if name not in TOOL_FUNCTIONS:
        return json.dumps({"status": "error", "error_message": f"Unknown tool: {name}"})

    try:
        func = TOOL_FUNCTIONS[name]
        result = func(**arguments)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error_message": str(e)})


# ============================================================================
# Chat Session Management
# ============================================================================

CHAT_SESSIONS_DIR = Path(__file__).parent / "chat_sessions"
CHAT_SESSIONS_DIR.mkdir(exist_ok=True)


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system", "tool"
    content: Optional[str] = None
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_calls: list = []


class StreamChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


def load_session(session_id: str) -> list:
    """Load chat session from disk."""
    session_file = CHAT_SESSIONS_DIR / f"{session_id}.json"
    if session_file.exists():
        with open(session_file) as f:
            return json.load(f)
    return [{"role": "system", "content": SYSTEM_INSTRUCTION}]


def save_session(session_id: str, messages: list):
    """Save chat session to disk."""
    session_file = CHAT_SESSIONS_DIR / f"{session_id}.json"
    with open(session_file, "w") as f:
        json.dump(messages, f, indent=2)


def generate_session_id() -> str:
    """Generate a unique session ID."""
    import uuid
    return str(uuid.uuid4())[:12]


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message and get a response (non-streaming)."""
    client = OpenAI()
    tools = build_tools_list()

    # Get or create session
    session_id = request.session_id or generate_session_id()
    messages = load_session(session_id)

    # Add user message
    messages.append({"role": "user", "content": request.message})

    max_iterations = 10
    iterations = 0
    all_tool_calls = []

    while iterations < max_iterations:
        iterations += 1

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        message = response.choices[0].message

        if message.tool_calls:
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })

            # Execute each tool call
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                result = execute_tool(func_name, func_args)
                all_tool_calls.append({
                    "name": func_name,
                    "arguments": func_args,
                    "result": json.loads(result) if result else None
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
        else:
            # Final response
            messages.append({
                "role": "assistant",
                "content": message.content
            })
            save_session(session_id, messages)

            return ChatResponse(
                session_id=session_id,
                response=message.content or "",
                tool_calls=all_tool_calls
            )

    save_session(session_id, messages)
    return ChatResponse(
        session_id=session_id,
        response="I've reached the maximum number of tool calls. Please try a simpler request.",
        tool_calls=all_tool_calls
    )


@router.post("/stream")
async def stream_message(request: StreamChatRequest):
    """Send a message and get a streaming response with tool call updates."""

    async def generate() -> AsyncGenerator[str, None]:
        client = OpenAI()
        tools = build_tools_list()

        session_id = request.session_id or generate_session_id()
        messages = load_session(session_id)

        # Send session ID first
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        messages.append({"role": "user", "content": request.message})

        max_iterations = 10
        iterations = 0

        while iterations < max_iterations:
            iterations += 1

            # Non-streaming for tool calls, streaming for final response
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            message = response.choices[0].message

            if message.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })

                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    try:
                        func_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        func_args = {}

                    # Notify about tool call
                    yield f"data: {json.dumps({'type': 'tool_start', 'name': func_name, 'arguments': func_args})}\n\n"

                    result = execute_tool(func_name, func_args)

                    # Notify about tool result
                    yield f"data: {json.dumps({'type': 'tool_result', 'name': func_name, 'result': json.loads(result) if result else None})}\n\n"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

                    await asyncio.sleep(0.01)  # Small delay between tool calls
            else:
                # Stream the final response
                content = message.content or ""

                # Send in chunks for streaming effect
                words = content.split(" ")
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.02)

                messages.append({
                    "role": "assistant",
                    "content": content
                })
                save_session(session_id, messages)

                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

        save_session(session_id, messages)
        yield f"data: {json.dumps({'type': 'error', 'message': 'Max iterations reached'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


class ChatSession(BaseModel):
    id: str
    title: str
    created_at: str
    message_count: int


@router.get("/sessions", response_model=list[ChatSession])
async def list_sessions():
    """List all chat sessions."""
    sessions = []

    for session_file in CHAT_SESSIONS_DIR.glob("*.json"):
        try:
            with open(session_file) as f:
                messages = json.load(f)

            # Generate title from first user message
            title = "New Chat"
            for msg in messages:
                if msg.get("role") == "user":
                    title = msg.get("content", "")[:50]
                    if len(msg.get("content", "")) > 50:
                        title += "..."
                    break

            sessions.append(ChatSession(
                id=session_file.stem,
                title=title,
                created_at=datetime.fromtimestamp(session_file.stat().st_mtime).isoformat(),
                message_count=len([m for m in messages if m.get("role") in ["user", "assistant"]])
            ))
        except Exception:
            continue

    # Sort by most recent
    sessions.sort(key=lambda s: s.created_at, reverse=True)
    return sessions


class SessionMessages(BaseModel):
    session_id: str
    messages: list


@router.get("/sessions/{session_id}", response_model=SessionMessages)
async def get_session(session_id: str):
    """Get messages for a specific session."""
    session_file = CHAT_SESSIONS_DIR / f"{session_id}.json"

    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    messages = load_session(session_id)

    # Filter to only user/assistant messages for display
    display_messages = [
        {"role": m["role"], "content": m.get("content", "")}
        for m in messages
        if m.get("role") in ["user", "assistant"] and m.get("content")
    ]

    return SessionMessages(session_id=session_id, messages=display_messages)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    session_file = CHAT_SESSIONS_DIR / f"{session_id}.json"

    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    session_file.unlink()
    return {"success": True, "message": f"Session {session_id} deleted"}


@router.post("/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    """Clear a session's history but keep the session."""
    session_file = CHAT_SESSIONS_DIR / f"{session_id}.json"

    if not session_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Reset to just system message
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    save_session(session_id, messages)

    return {"success": True, "message": "Session cleared"}


@router.get("/tools")
async def list_available_tools():
    """List all available tools with their descriptions."""
    tools = build_tools_list()

    return {
        "tools": [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "parameters": list(t["function"]["parameters"].get("properties", {}).keys())
            }
            for t in tools
        ],
        "count": len(tools)
    }
