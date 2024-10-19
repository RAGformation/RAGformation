import subprocess
from llama_index.llms.openai import OpenAI
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from typing import Dict, Any, List
import config
from prompts import fix_import_prompt_template, fix_and_write_code_template
from raw_tool_fuctions.diagram_tools import text_to_diagram, write_to_file

def run_and_check_syntax(*args, **kwargs) -> str:
    """
    Run the generated diagram code and check for syntax errors.
    
    Args:
    ctx (Dict[str, Any]): The context containing the current state and data.
    
    Returns:
    str: A message indicating whether the syntax is correct or describing any errors encountered.
    """
    ctx = kwargs.get('ctx')
    try:
        result = subprocess.run(
            [config.PYTHON_PATH, "temp_generated_code.py"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            response = "Syntax is correct."
        else:
            response = f"Error encountered: {result.stderr}"
        ctx.data['query'] += f"\n\n{response}"
    except Exception as e:
        response = f"Exception occurred: {str(e)}"
        ctx.data['query'] += f"\n\n{response}"
    return response

def suggest_imports(*args, **kwargs) -> str:
    """
    Suggest correct imports based on the error message.
    
    Args:
    ctx (Dict[str, Any]): The context containing the current state and data.
    
    Returns:
    str: The error message or suggested imports.
    """
    ctx = kwargs.get('ctx')

    print("Checking syntax for the provided code")
    last_msg = ctx.data['query'].split("\n\n")[-1].lower()
    last_second_msg = ctx.data['query'].split("\n\n")[-2].lower()
    
    if "error" in last_msg or "exception" in last_msg:
        error_message = last_msg
    elif "error" in last_second_msg or "exception" in last_second_msg:
        error_message = last_second_msg
    else:
        return "No error message found."

    print(f"Error message: {error_message}")

    index = LlamaCloudIndex(
        name="import-shema", 
        project_name="Default",
        organization_id=os.environ["PINECONE_API_KEY"],
        api_key=os.environ["PINECONE_ORGANIZATION_ID"]
    )

    query = fix_import_prompt_template.format(error_txt=error_message)
    response = index.as_query_engine().query(query)
    response = f"The correct import should be {response}"
    print(response)
    ctx.data['query'] += f"\n\n{response}"
    return error_message

def fix_and_write_code(*args, **kwargs) -> str:
    """
    Fix errors in the code and write the corrected code to a file.
    
    Args:
    ctx (Dict[str, Any]): The context containing the current state and data.
    
    Returns:
    str: A message indicating the result of the operation.
    """
    ctx = kwargs.get('ctx')

    try:
        last_msg = ctx.data['query'].split("\n\n")[-1].lower()
        last_second_msg = ctx.data['query'].split("\n\n")[-2].lower()
        if "error" in last_msg or "exception" in last_msg:
            error_message = last_msg
        elif "error" in last_second_msg or "exception" in last_second_msg:
            error_message = last_second_msg
        else:
            error_message = ctx.data['query']

        input_filename: str = "temp_generated_code.py"
        output_filename: str = "temp_generated_code.py"

        with open(input_filename, "r") as file:
            original_code = file.read()

        llm = OpenAI(model="gpt-4-turbo-preview")
        prompt = fix_and_write_code_template.format(
            original_code=original_code, error_message=error_message
        )
        resp = str(llm.complete(prompt))

        write_result = write_to_file(str(resp), output_filename)

        response = f"Code fixed and written to {output_filename}."
        ctx.data['query'] += f"\n\n{response}"
        return ctx.data['query']

    except Exception as e:
        response = f"Failed to fix and write code: {str(e)}"
        ctx.data['query'] += f"\n\n{response}"
        return ctx.data['query']

def generate_diagram(*args, **kwargs) -> str:
    """
    Generate a diagram based on the text description in the context.
    
    Args:
    ctx (Dict[str, Any]): The context containing the current state and data.
    
    Returns:
    str: A message indicating the result of the diagram generation.
    """
    ctx = kwargs.get('ctx')

    text = ctx["rag_search_response"]
    print("Generating diagram...")
    print(f"Generating diagram query: {text}")

    text = ctx['history']

    resp = text_to_diagram(text)
    print(f"Generating diagram response: {resp}")

    if "successfully" in resp.lower():
        ctx["diagram_syntax_error"] = None
        response = "Output diagram saved to output_diagram.png"
    else:
        ctx["diagram_syntax_error"] = f"Error encountered: {resp}"
        response = f"Error encountered: {resp}"
    ctx.data['query'] += f"\n\n{response}"
    return ctx.data['query']