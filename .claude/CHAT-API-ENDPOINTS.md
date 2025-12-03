# Chat API Endpoints Reference

**File**: `backend/chat_api.py` (797 lines)
**Router**: `/api/chat`

This document describes all chat/agent endpoints for the AI assistant.

---

## Overview

The chat API provides an AI agent interface powered by OpenAI GPT-5.1. The agent can:
- Answer questions about data, models, and workflows
- Execute actions using tool calls
- Stream responses in real-time
- Manage chat sessions
- Generate artifacts (graphs, reports)

**Model**: `gpt-5.1` (configured in `settings/constants.py`)

---

## Endpoints

### `POST /api/chat/send`
**Description**: Send message and get complete response (non-streaming)

**Request**:
```json
{
  "message": "What data do I have available?",
  "session_id": "uuid"  // Optional - creates new session if omitted
}
```

**Response**:
```json
{
  "response": "You have 3 processed labels: damaged, healthy, baseline...",
  "session_id": "uuid",
  "tool_calls": [
    {
      "name": "list_datasets",
      "arguments": {},
      "result": { "status": "success", ... }
    }
  ],
  "artifacts": [
    {
      "type": "image",
      "name": "accuracy_graph.png",
      "data": "base64...",
      "format": "png"
    }
  ]
}
```

**Use Case**: Simple request-response (no streaming)

---

### `POST /api/chat/stream`
**Description**: Send message and stream response (SSE)

**Request**: Same as `/send`

**Response**: Server-Sent Events (SSE) stream
```
data: {"type": "session", "session_id": "uuid"}

data: {"type": "tool_start", "name": "list_datasets", "arguments": {}}

data: {"type": "tool_result", "name": "list_datasets", "result": {...}}

data: {"type": "content", "content": "You have 3"}

data: {"type": "content", "content": " processed labels"}

data: {"type": "artifact", "artifact": {"type": "image", ...}}

data: {"type": "done"}
```

**Event Types**:
- `session` - Session created/identified
- `tool_start` - Agent calling a tool
- `tool_result` - Tool execution complete
- `content` - Text chunk (incremental)
- `artifact` - Graph/report generated
- `done` - Response complete
- `error` - Error occurred

**Use Case**: Real-time chat interface with progress indicators

**Frontend Example**:
```typescript
const response = await fetch('/api/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message, session_id }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  const lines = text.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));

      switch (event.type) {
        case 'content':
          appendContent(event.content);
          break;
        case 'tool_start':
          showToolIndicator(event.name);
          break;
        case 'artifact':
          displayArtifact(event.artifact);
          break;
      }
    }
  }
}
```

---

### `GET /api/chat/sessions`
**Description**: List all chat sessions

**Response**:
```json
[
  {
    "id": "uuid",
    "title": "Data analysis discussion",
    "created_at": "2025-01-15T10:30:00Z",
    "message_count": 12
  }
]
```

**Session Title**: Automatically generated from first message

**Storage**: `backend/chat_sessions/{session_id}.json`

---

### `GET /api/chat/sessions/{session_id}`
**Description**: Get session history

**Response**:
```json
{
  "session_id": "uuid",
  "messages": [
    {
      "role": "user",
      "content": "What data do I have?",
      "timestamp": "2025-01-15T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "You have 3 processed labels...",
      "timestamp": "2025-01-15T10:30:05Z",
      "tool_calls": [...],
      "artifacts": [...]
    }
  ]
}
```

**Errors**: 404 if session not found

---

### `DELETE /api/chat/sessions/{session_id}`
**Description**: Delete chat session

**Response**:
```json
{
  "success": true,
  "message": "Session deleted"
}
```

**Action**: Deletes session file

---

### `POST /api/chat/sessions/{session_id}/clear`
**Description**: Clear session messages (keep session)

**Response**:
```json
{
  "success": true,
  "message": "Session cleared"
}
```

**Action**: Removes all messages but keeps session

---

### `GET /api/chat/tools`
**Description**: List all available agent tools

**Response**:
```json
[
  {
    "name": "list_datasets",
    "description": "List all processed datasets/labels",
    "parameters": {
      "type": "object",
      "properties": {},
      "required": []
    }
  },
  {
    "name": "run_inference",
    "description": "Run inference on a test file",
    "parameters": {
      "type": "object",
      "properties": {
        "csv_path": { "type": "string" },
        "model_id": { "type": "string" },
        "notes": { "type": "string" }
      },
      "required": ["csv_path", "model_id"]
    }
  }
]
```

**Use Case**: Debug agent capabilities, API documentation

---

## Agent Tools

Tools available to the agent (see `SERVER.md` for full list):

**Data Management** (9 tools):
- `list_datasets()` - List processed labels
- `get_dataset_details(label)` - Get label info
- `list_available_data()` - Show all uploaded data
- `suggest_label(folder_path)` - AI suggest label
- `ingest_data(folder_path, label)` - Process raw data
- `delete_dataset(label)` - Delete label
- `generate_dataset_metadata(label)` - Generate metadata
- `list_raw_folders()` - List raw uploads

**Model Training** (7 tools):
- `list_models()` - List models
- `get_model_details(model_id)` - Get model info
- `suggest_model_name(labels)` - AI suggest name
- `start_training(labels, model_name, params)` - Train
- `get_training_status(job_id)` - Check progress
- `wait_for_training(job_id)` - Wait for completion
- `delete_model(model_id)` - Delete model

**Inference/Testing** (5 tools):
- `run_inference(csv_path, model_id, notes, tags)` - Test
- `list_tests()` - List tests
- `get_test_details(test_id)` - Get test info
- `get_test_statistics(test_ids)` - Compare tests
- `delete_test(test_id)` - Delete test

**Analysis & Reports** (12 tools):
- `get_workflow_guidance()` - Workflow help
- `compare_models(model_ids)` - Compare models
- `get_dataset_summary(label)` - Dataset stats
- `get_training_recommendations(labels)` - Training advice
- `explain_results(test_id)` - Explain predictions
- `get_model_graphs(model_id)` - Training graphs
- `get_report_url(model_id)` - Report URL
- `read_pdf(url)` - Read PDF
- `read_report(model_id)` - Read model report
- `list_reports()` - List reports
- `get_system_status()` - System status

---

## Tool Execution Flow

1. **User sends message**: "Train a model on damaged and healthy data"

2. **Agent plans**: Determines which tools to call
   ```
   Tools needed:
   1. list_datasets() - verify data exists
   2. suggest_model_name(["damaged", "healthy"]) - get name
   3. start_training(...) - start training
   ```

3. **Tool execution** (sequential):
   ```
   Event: tool_start { name: "list_datasets" }
   Event: tool_result { result: { datasets: [...] } }
   Event: tool_start { name: "suggest_model_name" }
   Event: tool_result { result: { name: "2class_detector" } }
   Event: tool_start { name: "start_training" }
   Event: tool_result { result: { job_id: "uuid" } }
   ```

4. **Response generation**:
   ```
   Event: content { "I've started training..." }
   Event: done
   ```

---

## Artifacts

Artifacts are generated during agent responses (graphs, reports, etc.)

**Artifact Types**:

### Image Artifact
```json
{
  "type": "image",
  "name": "accuracy_graph.png",
  "data": "iVBORw0KGgoAAAANS...",  // base64
  "format": "png"
}
```

**Display**:
```typescript
<img src={`data:image/${artifact.format};base64,${artifact.data}`} />
```

### Report Artifact
```json
{
  "type": "report",
  "name": "Training Report",
  "url": "/api/training/report/view?model_id=2class_detector",
  "filename": "training_report_2class_detector.pdf"
}
```

**Display**:
```typescript
<iframe src={artifact.url} />
// Or download link
<a href={artifact.url.replace('/view?', '/download?')}>Download</a>
```

---

## Session Management

### Session Creation
- Auto-created on first message if no `session_id` provided
- Session ID returned in response
- Title auto-generated from first message

### Session Storage
```
backend/chat_sessions/
└── {session_id}.json
    {
      "session_id": "uuid",
      "created_at": "2025-01-15T10:30:00Z",
      "title": "Data analysis discussion",
      "messages": [...]
    }
```

### Session Persistence
- Sessions persist across server restarts
- Frontend stores `session_id` in localStorage
- On reload, frontend loads session messages

---

## Error Handling

**Error Event**:
```json
{
  "type": "error",
  "error": "Tool execution failed",
  "message": "Model not found: invalid_model"
}
```

**Common Errors**:
- Tool execution fails (e.g., file not found)
- OpenAI API error (rate limit, invalid request)
- Invalid session ID
- Missing required parameters

**Frontend Handling**:
```typescript
switch (event.type) {
  case 'error':
    toast({
      title: "Error",
      description: event.message,
      variant: "destructive",
    });
    break;
}
```

---

## System Instruction

The agent's system prompt is defined in `agent/damage_lab_agent.py` as `SYSTEM_INSTRUCTION`.

**Key points**:
- You are a helpful assistant for sensor data analysis
- You help manage data, train models, and run tests
- Use tools to perform actions
- Provide clear, concise explanations
- Guide users through workflows

**Workflow Guidance**:
The agent knows common workflows:
1. **Data Ingestion**: list_available_data → suggest_label → ingest_data
2. **Model Training**: list_datasets → start_training → wait_for_training
3. **Testing**: run_inference → get_test_details → explain_results

---

## OpenAI Configuration

**Model**: `gpt-5.1` (from `settings/constants.py`)

**Important**:
- DO NOT use `max_tokens` parameter (not supported by gpt-5.1)
- DO NOT hardcode model name (use `OPENAI_MODEL` constant)

**Tool Calling**:
```python
from openai import OpenAI
from settings.constants import OPENAI_MODEL

client = OpenAI()
response = client.chat.completions.create(
    model=OPENAI_MODEL,  # "gpt-5.1"
    messages=[...],
    tools=[...],
    # NO max_tokens parameter
)
```

---

## Frontend Integration

### React Query
```typescript
// Send message
const mutation = useMutation({
  mutationFn: async ({ message, session_id }) => {
    const res = await fetch('/api/chat/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id }),
    });
    return res.json();
  },
});

// List sessions
const { data: sessions } = useQuery({
  queryKey: ['/api/chat/sessions'],
});
```

### Streaming
```typescript
async function* streamChat(message: string, sessionId?: string) {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const event = JSON.parse(line.slice(6));
        yield event;
      }
    }
  }
}
```

---

## Testing

### Manual Testing
```bash
# Send message
curl -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "What data do I have?"}'

# List sessions
curl http://localhost:8000/api/chat/sessions

# Get session
curl http://localhost:8000/api/chat/sessions/{session_id}

# Stream (watch events)
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Train a model"}' \
  --no-buffer
```

### Tool Testing
```bash
# List available tools
curl http://localhost:8000/api/chat/tools | jq
```

---

## Quick Reference

**Send Message**:
```
POST /api/chat/send
POST /api/chat/stream  (SSE)
```

**Manage Sessions**:
```
GET    /api/chat/sessions
GET    /api/chat/sessions/{id}
DELETE /api/chat/sessions/{id}
POST   /api/chat/sessions/{id}/clear
```

**Tools**:
```
GET /api/chat/tools
```

**Event Types** (streaming):
- `session` - Session info
- `tool_start` - Tool called
- `tool_result` - Tool finished
- `content` - Text chunk
- `artifact` - Graph/report
- `done` - Complete
- `error` - Error
