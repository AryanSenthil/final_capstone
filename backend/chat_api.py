"""
Chat API Router for Aryan Senthil's App
=======================================
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
    list_available_data,
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
    get_model_graphs,
    get_report_url,
    read_pdf,
    read_report,
    list_reports,
    get_system_status,
    SYSTEM_INSTRUCTION,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Map of function names to actual functions
TOOL_FUNCTIONS = {
    "list_datasets": list_datasets,
    "get_dataset_details": get_dataset_details,
    "list_available_data": list_available_data,
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
    "get_model_graphs": get_model_graphs,
    "get_report_url": get_report_url,
    "read_pdf": read_pdf,
    "read_report": read_report,
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


def truncate_large_content(content: str, max_length: int = 5000) -> str:
    """
    Truncate large content (like base64 images) to prevent token overflow.
    Detects base64 data and replaces with placeholder.
    """
    if not content:
        return content

    # Check if content contains base64 image data
    if "data:image" in content and "base64," in content:
        # Extract everything before the base64 data
        parts = content.split("base64,")
        if len(parts) > 1:
            return parts[0] + "base64,[BASE64_IMAGE_DATA_TRUNCATED]"

    # Check for large JSON with base64 fields
    if len(content) > max_length and ("base64" in content.lower() or "data:image" in content):
        try:
            data = json.loads(content)
            # Truncate any base64 fields
            if isinstance(data, dict):
                for key in data:
                    if isinstance(data[key], str) and len(data[key]) > 1000:
                        if data[key].startswith("data:image") or "base64" in key.lower():
                            data[key] = "[BASE64_DATA_TRUNCATED]"
                return json.dumps(data)
        except:
            pass

    # If still too large, truncate with message
    if len(content) > max_length:
        return content[:max_length] + f"\n\n[TRUNCATED - {len(content) - max_length} more characters]"

    return content


def estimate_token_count(messages: list) -> int:
    """
    Rough estimate of token count for messages.
    Approximation: 1 token ≈ 4 characters
    """
    total_chars = 0
    for msg in messages:
        if isinstance(msg.get("content"), str):
            total_chars += len(msg["content"])
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                total_chars += len(str(tc))
    return total_chars // 4


async def summarize_old_messages(client: OpenAI, messages: list, keep_recent: int = 10) -> list:
    """
    Summarize older messages to reduce token count.
    Keeps system message, recent messages, and creates a summary of the middle.

    Args:
        client: OpenAI client
        messages: Full message history
        keep_recent: Number of recent messages to keep as-is

    Returns:
        Condensed message list with summary
    """
    if len(messages) <= keep_recent + 1:  # +1 for system message
        return messages

    # Separate system message, old messages, and recent messages
    system_msg = messages[0] if messages[0]["role"] == "system" else None
    start_idx = 1 if system_msg else 0

    if len(messages) - start_idx <= keep_recent:
        return messages

    old_messages = messages[start_idx:-keep_recent]
    recent_messages = messages[-keep_recent:]

    # Create summary of old messages
    summary_prompt = f"""Summarize this conversation history concisely. Focus on:
1. Key actions taken (datasets created, models trained, tests run)
2. Important findings or results
3. User's goals and context

Conversation to summarize:
{json.dumps(old_messages, indent=2)}

Provide a brief summary (2-3 paragraphs max):"""

    try:
        summary_response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations concisely."},
                {"role": "user", "content": summary_prompt}
            ]
        )
        summary = summary_response.choices[0].message.content

        # Build new message list with summary
        new_messages = []
        if system_msg:
            new_messages.append(system_msg)

        new_messages.append({
            "role": "system",
            "content": f"Previous conversation summary:\n{summary}\n\nContinuing from here with recent messages..."
        })

        new_messages.extend(recent_messages)

        return new_messages

    except Exception as e:
        print(f"Failed to summarize messages: {e}")
        # Fallback: just keep recent messages
        result = []
        if system_msg:
            result.append(system_msg)
        result.extend(recent_messages)
        return result


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message and get a response (non-streaming)."""
    try:
        client = OpenAI()
    except Exception as e:
        error_msg = str(e)
        if "api" in error_msg.lower() or "key" in error_msg.lower():
            raise HTTPException(
                status_code=401,
                detail="OpenAI API Error: Please check your API key and billing status. This is usually caused by an invalid API key or insufficient credits."
            )
        raise HTTPException(status_code=500, detail=f"OpenAI initialization error: {error_msg}")

    tools = build_tools_list()

    # Get or create session
    session_id = request.session_id or generate_session_id()
    messages = load_session(session_id)

    # Add user message
    messages.append({"role": "user", "content": request.message})

    # Check token count and summarize if needed
    estimated_tokens = estimate_token_count(messages)
    TOKEN_LIMIT = 200000  # Conservative limit (gpt-4o has 270k context)

    if estimated_tokens > TOKEN_LIMIT:
        print(f"Token count ({estimated_tokens}) exceeds limit. Summarizing conversation...")
        messages = await summarize_old_messages(client, messages, keep_recent=15)
        # Save the summarized session
        save_session(session_id, messages)
        print(f"Summarized. New token count: {estimate_token_count(messages)}")

    max_iterations = 10
    iterations = 0
    all_tool_calls = []

    while iterations < max_iterations:
        iterations += 1

        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
        except Exception as e:
            error_msg = str(e)
            if "insufficient_quota" in error_msg.lower() or "billing" in error_msg.lower():
                raise HTTPException(
                    status_code=402,
                    detail="OpenAI API Error: Your account has insufficient credits or billing issues. Please add credits to your OpenAI account."
                )
            elif "invalid" in error_msg.lower() and "key" in error_msg.lower():
                raise HTTPException(
                    status_code=401,
                    detail="OpenAI API Error: Invalid API key. Please check your API key configuration."
                )
            elif "rate_limit" in error_msg.lower():
                raise HTTPException(
                    status_code=429,
                    detail="OpenAI API Error: Rate limit exceeded. Please try again in a moment."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"OpenAI API Error: {error_msg}"
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

                # Truncate large content (base64 images, PDFs) before saving to history
                truncated_result = truncate_large_content(result) if result else result

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": truncated_result
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
        try:
            client = OpenAI()
        except Exception as e:
            error_msg = str(e)
            if "api" in error_msg.lower() or "key" in error_msg.lower():
                yield f"data: {json.dumps({'type': 'error', 'error': 'OpenAI API Error: Please check your API key and billing status. This is usually caused by an invalid API key or insufficient credits.'})}\n\n"
                return
            yield f"data: {json.dumps({'type': 'error', 'error': f'OpenAI initialization error: {error_msg}'})}\n\n"
            return

        tools = build_tools_list()

        session_id = request.session_id or generate_session_id()
        messages = load_session(session_id)

        # Send session ID first
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        messages.append({"role": "user", "content": request.message})

        # Track artifacts across all tool calls for this response
        collected_artifacts = []

        # Check token count and summarize if needed
        estimated_tokens = estimate_token_count(messages)
        TOKEN_LIMIT = 200000  # Conservative limit

        if estimated_tokens > TOKEN_LIMIT:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Conversation is long. Summarizing older messages...'})}\n\n"
            messages = await summarize_old_messages(client, messages, keep_recent=15)
            save_session(session_id, messages)
            yield f"data: {json.dumps({'type': 'status', 'message': 'Summary complete. Continuing...'})}\n\n"

        max_iterations = 10
        iterations = 0

        while iterations < max_iterations:
            iterations += 1

            # Non-streaming for tool calls, streaming for final response
            try:
                response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto"
                )
            except Exception as e:
                error_msg = str(e)
                if "insufficient_quota" in error_msg.lower() or "billing" in error_msg.lower():
                    yield f"data: {json.dumps({'type': 'error', 'error': 'OpenAI API Error: Your account has insufficient credits or billing issues. Please add credits to your OpenAI account.'})}\n\n"
                elif "invalid" in error_msg.lower() and "key" in error_msg.lower():
                    yield f"data: {json.dumps({'type': 'error', 'error': 'OpenAI API Error: Invalid API key. Please check your API key configuration.'})}\n\n"
                elif "rate_limit" in error_msg.lower():
                    yield f"data: {json.dumps({'type': 'error', 'error': 'OpenAI API Error: Rate limit exceeded. Please try again in a moment.'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'error': f'OpenAI API Error: {error_msg}'})}\n\n"
                return

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
                    result_parsed = json.loads(result) if result else None

                    # Notify about tool result
                    yield f"data: {json.dumps({'type': 'tool_result', 'name': func_name, 'result': result_parsed})}\n\n"

                    # Check for artifacts in the result and emit them
                    if result_parsed and isinstance(result_parsed, dict) and "artifacts" in result_parsed:
                        artifacts = result_parsed.get("artifacts", [])
                        for artifact in artifacts:
                            if artifact:  # Filter out None artifacts
                                collected_artifacts.append(artifact)
                                yield f"data: {json.dumps({'type': 'artifact', 'artifact': artifact})}\n\n"

                    # Truncate large content (base64 images, PDFs) before saving to history
                    truncated_result = truncate_large_content(result) if result else result

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": truncated_result
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

                # Save assistant message with artifacts
                assistant_message = {
                    "role": "assistant",
                    "content": content
                }
                if collected_artifacts:
                    assistant_message["artifacts"] = collected_artifacts

                messages.append(assistant_message)
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

    # Filter to only user/assistant messages for display, include artifacts if present
    display_messages = []
    for m in messages:
        if m.get("role") in ["user", "assistant"] and m.get("content"):
            msg = {"role": m["role"], "content": m.get("content", "")}
            # Include artifacts if they exist
            if "artifacts" in m:
                msg["artifacts"] = m["artifacts"]
            display_messages.append(msg)

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
