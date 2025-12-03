"""
Aryan Senthil's Chat Interface
===============================
A standalone chat interface for Aryan Senthil's sensor data application.
Uses OpenAI API directly with function calling for tool execution.

Usage:
    python chat_runner.py

Environment Variables:
    OPENAI_API_KEY: Your OpenAI API key
"""

import os
import json
import inspect
from typing import Callable, Any
from openai import OpenAI

# Import all tools from the agent module
from damage_lab_agent import (
    # Data Management
    list_datasets,
    get_dataset_details,
    list_available_data,
    suggest_label,
    ingest_data,
    delete_dataset,
    generate_dataset_metadata,
    list_raw_folders,
    # Model Training
    list_models,
    get_model_details,
    suggest_model_name,
    start_training,
    get_training_status,
    wait_for_training,
    delete_model,
    # Inference/Testing
    run_inference,
    list_tests,
    get_test_details,
    get_test_statistics,
    delete_test,
    # Enhanced Analysis
    get_workflow_guidance,
    compare_models,
    get_dataset_summary,
    get_training_recommendations,
    explain_results,
    # Reporting & System
    get_model_graphs,
    get_report_url,
    read_pdf,
    read_report,
    list_reports,
    get_system_status,
    # Constants
    SYSTEM_INSTRUCTION,
)


# OpenAI model to use
MODEL = "gpt-5.1"


# Map of function names to actual functions
TOOL_FUNCTIONS: dict[str, Callable] = {
    # Data Management
    "list_datasets": list_datasets,
    "get_dataset_details": get_dataset_details,
    "list_available_data": list_available_data,
    "suggest_label": suggest_label,
    "ingest_data": ingest_data,
    "delete_dataset": delete_dataset,
    "generate_dataset_metadata": generate_dataset_metadata,
    "list_raw_folders": list_raw_folders,
    # Model Training
    "list_models": list_models,
    "get_model_details": get_model_details,
    "suggest_model_name": suggest_model_name,
    "start_training": start_training,
    "get_training_status": get_training_status,
    "wait_for_training": wait_for_training,
    "delete_model": delete_model,
    # Inference/Testing
    "run_inference": run_inference,
    "list_tests": list_tests,
    "get_test_details": get_test_details,
    "get_test_statistics": get_test_statistics,
    "delete_test": delete_test,
    # Enhanced Analysis
    "get_workflow_guidance": get_workflow_guidance,
    "compare_models": compare_models,
    "get_dataset_summary": get_dataset_summary,
    "get_training_recommendations": get_training_recommendations,
    "explain_results": explain_results,
    # Reporting & System
    "get_model_graphs": get_model_graphs,
    "get_report_url": get_report_url,
    "read_pdf": read_pdf,
    "read_report": read_report,
    "list_reports": list_reports,
    "get_system_status": get_system_status,
}


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
        # Extract inner type
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
    
    # Build parameters schema
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        if param_name in ["self", "cls"]:
            continue
        
        param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
        schema = python_type_to_json_schema(param_type)
        
        # Add description from docstring
        if param_name in param_docs:
            schema["description"] = param_docs[param_name]
        
        properties[param_name] = schema
        
        # Check if required (no default value and not Optional)
        if param.default == inspect.Parameter.empty:
            if "Optional" not in str(param_type):
                required.append(param_name)
    
    # Extract first line of docstring as description
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
    for func in TOOL_FUNCTIONS.values():
        tools.append(function_to_tool_spec(func))
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


class DamageLabChat:
    """Interactive chat interface for Aryan Senthil's app."""
    
    def __init__(self):
        self.client = OpenAI()
        self.tools = build_tools_list()
        self.messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION}
        ]
        self.max_tool_iterations = 10
    
    def chat(self, user_message: str) -> str:
        """Process a user message and return the assistant's response."""
        self.messages.append({"role": "user", "content": user_message})
        
        iterations = 0
        while iterations < self.max_tool_iterations:
            iterations += 1
            
            # Call the model
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Check if we need to call tools
            if message.tool_calls:
                # Add assistant message with tool calls
                self.messages.append({
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
                    
                    print(f"  [Calling {func_name}...]")
                    result = execute_tool(func_name, func_args)
                    
                    # Add tool result
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
            else:
                # No more tool calls, return the response
                self.messages.append({
                    "role": "assistant",
                    "content": message.content
                })
                return message.content
        
        return "I've reached the maximum number of tool calls. Please try a simpler request."
    
    def reset(self):
        """Reset conversation history."""
        self.messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION}
        ]


def print_banner():
    """Print welcome banner."""
    print()
    print("=" * 70)
    print("  DAMAGE LAB CHAT INTERFACE")
    print("  Neural Network Training & Inference for Sensor Data")
    print("=" * 70)
    print()
    print("Commands:")
    print("  'quit' or 'exit'  - Exit the chat")
    print("  'reset'           - Clear conversation history")
    print("  'status'          - Check API connection")
    print()
    print("Example queries:")
    print("  - 'What datasets do we have?'")
    print("  - 'Show me all trained models'")
    print("  - 'Train a CNN model on crushcore and disbond data'")
    print("  - 'Run inference on /path/to/test.csv using my_model'")
    print()
    print("-" * 70)
    print()


def main():
    """Main entry point for the chat interface."""
    print_banner()
    
    # Check API status
    status = get_system_status()
    if status["status"] == "success":
        print(f"Connected to Aryan Senthil's API at {status['api_url']}")
    else:
        print(f"Warning: Could not connect to API")
        print(f"  Error: {status.get('error_message', 'Unknown')}")
        print("  Make sure the FastAPI server is running (python api.py)")
    print()
    
    chat = DamageLabChat()
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            if user_input.lower() == 'reset':
                chat.reset()
                print("Conversation reset.\n")
                continue
            
            if user_input.lower() == 'status':
                status = get_system_status()
                print(f"\n{json.dumps(status, indent=2)}\n")
                continue
            
            print()
            response = chat.chat(user_input)
            print(f"\nAssistant: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
