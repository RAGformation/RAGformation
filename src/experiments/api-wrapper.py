from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from enum import Enum
from typing import List, Optional, Union
import fastapi
import json
import logging
import subprocess
import sys
import time
import uuid
import uvicorn

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger().name = __name__

app = FastAPI()

# Start the subprocess that will run your workflows script
proc = subprocess.Popen(
    ["python", "workflows.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
    universal_newlines=True,
)


class MessageRole(Enum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: MessageRole = MessageRole.USER
    content: Optional[str] = ""
    id: Optional[str] = None
    additional_kwargs: dict = {}


class ChatCompletionsRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    logprobs: Optional[int] = None
    echo: Optional[bool] = None
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    user: Optional[str] = None
    stream: Optional[bool] = False


class CustomStreamingResponse(fastapi.responses.StreamingResponse):
    def __init__(self, content, *args, **kwargs):
        super().__init__(content, *args, **kwargs)
        # Set custom headers
        self.headers["Cache-Control"] = "no-cache"
        self.headers["Connection"] = "keep-alive"
        self.headers["X-Accel-Buffering"] = "no"
        self.headers["Content-Type"] = "text/event-stream; charset=utf-8"
        self.headers["OpenAI-Processing-ms"] = "658"  # This should ideally be dynamic
        self.headers["X-Request-ID"] = str(uuid.uuid4()).replace(
            "-", ""
        )  # Generate a unique ID for each request
        self.headers["Transfer-Encoding"] = "chunked"


def filter_output_lines(lines):
    magenta_start = "\x1b[35m"
    magenta_reset = "\x1b[0m"
    response_lines = []
    debug_lines = []

    # Process each line to determine if it is a response or debug
    inside_magenta = False
    for line in lines:
        if magenta_start in line:
            inside_magenta = True
            # Start extracting from where the magenta code ends
            clean_line = line.split(magenta_start)[1]  # Extract after magenta_start
            response_lines.append(clean_line)
        elif magenta_reset in line and inside_magenta:
            # Stop extracting and remove the magenta reset code
            clean_line = line.split(magenta_reset)[0]
            response_lines.append(clean_line)
            inside_magenta = False
        elif inside_magenta:
            # Keep appending lines until the magenta reset is found
            response_lines.append(line)

    return "".join(response_lines), "".join(debug_lines)


@app.post("/v1/concierge")
async def concierge(request: Request):
    body = await request.json()
    input_text = body.get("input")

    if input_text is None:
        raise HTTPException(status_code=400, detail="Input text is required")

    # Send input to the workflows subprocess
    print(input_text, file=proc.stdin, flush=True)

    # Read the response until the prompt appears
    output = []
    while True:
        line = proc.stdout.readline()
        if line.startswith("> "):
            break
        output.append(line)

    # Filter and separate the output into response and debug
    response_text, debug_text = filter_output_lines(output)
    return {"response": response_text, "debug": debug_text}


@app.api_route("/v1/chat/completions", methods=["POST"])
async def create_chat_completions(
    request_data: ChatCompletionsRequest, request: Request
):
    if request.headers.get("Content-Type") != "application/json":
        raise HTTPException(
            status_code=400, detail="Invalid Content-Type. Expected application/json."
        )

    # Extract the last user message
    last_user_message = next(
        (
            msg
            for msg in reversed(request_data.messages)
            if msg.role == MessageRole.USER
        ),
        None,
    )
    if not last_user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    # Send input to the workflows subprocess
    print(last_user_message.content, file=proc.stdin, flush=True)

    # Read the response until the prompt appears
    output = []
    while True:
        line = proc.stdout.readline()
        if line.startswith("> "):
            break
        output.append(line)

    logging.debug("output:", output)

    # Filter and separate the output into response and debug
    response_text, debug_text = filter_output_lines(output)

    message_id = f"msg-{int(time.time())}"
    created = int(time.time())

    if not request_data.stream:
        # Return the synchronous response
        return {
            "id": message_id,
            "object": "chat.completion",
            "created": created,
            "model": request_data.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text,
                    },
                    "finish_reason": "stop",
                }
            ],
        }

    else:
        # Handle streaming response
        def generate_responses():
            tokens = list(response_text)  # Assuming the response can be tokenized
            for i, token in enumerate(tokens):
                finish_reason = None if i < len(tokens) - 1 else "stop"
                choice = {
                    "delta": {
                        "content": f"{token}",
                    },
                    "index": 0,
                    "finish_reason": finish_reason,
                }
                chunk_data = {
                    "id": message_id,
                    "model": request_data.model,
                    "created": created,
                    "object": "chat.completion.chunk",
                    "choices": [choice],
                }
                chunk = f"data: {json.dumps(chunk_data)}\n\n"
                yield chunk

        return CustomStreamingResponse(
            generate_responses(), media_type="text/event-stream"
        )


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-4",
                "object": "model",
                "created": None,
                "description": "The latest generation of our state-of-the-art language models.",
            }
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
