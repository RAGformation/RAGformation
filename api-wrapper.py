from fastapi import FastAPI, HTTPException, Request
import subprocess
import uvicorn

app = FastAPI()

# Start the subprocess that will run your workflows script
proc = subprocess.Popen(
    ['python', 'workflows.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
    universal_newlines=True
)

def filter_output_lines(lines):
    magenta_start = '\x1b[35m'
    magenta_reset = '\x1b[0m'
    response_lines = []
    debug_lines = []

    # Process each line to determine if it is a response or debug
    for line in lines:
        if magenta_start in line:
            # Remove ANSI color codes for cleaner output
            clean_line = line.replace(magenta_start, '').replace(magenta_reset, '')
            response_lines.append(clean_line)
        else:
            debug_lines.append(line)

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
    return {
        "response": response_text,
        "debug": debug_text
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
