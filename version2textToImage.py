from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
# from llama_index.llms.mistralai import MistralAI
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.tools import QueryEngineTool
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
import sys
import os
import re
import subprocess

# from agent_scripts import text_to_diagram
from prompts import fix_import_prompt_template, txt_2_diagram_prompt_template


def run_script():
    """
    Run a the temp_generated_code.py script and capture its output or error message.

    This function executes the specified Python script using subprocess.
    If the script runs successfully, it returns "No errors".
    If the script raises an exception, it returns the error message.

    Args:
        None

    Returns:
        str: "No errors" if the script runs successfully, or the error message if it fails.
    """
    try:
        filename = "temp_generated_code.py"
        python_executable = os.path.join(os.environ['CONDA_PREFIX'], 'bin', 'python')
        python_executable = "/Users/kevintran/Downloads/RAGformation-main/myenv/bin/python"

        result = subprocess.run([python_executable, filename], 
                                capture_output=True, 
                                text=True, 
                                check=True)
        return "No errors"
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.strip()}"

def extract_code(text):
    # Pattern to match code blocks with or without language specification
    pattern = r'```(?:python)?\s*([\s\S]*?)\s*```'
    
    matches = re.findall(pattern, text, re.MULTILINE)
    return matches
    
def text_to_diagram(requirements_plan: str) -> str:
    """
    Automatically generates AWS architecture code and a corresponding visual diagram using the Diagrams Python library.
    
    Args:
        requirements_plan (str): A detailed description of the requirements for the AWS architecture.
    
    Returns:
        code_str (str): The generated Python code for the AWS architecture using the Diagrams library.
        diagram_image (Image): The generated image of the AWS architecture diagram
    """
    
    # llm = TogetherLLM(
    #     model="mistralai/Mixtral-8x7B-Instruct-v0.1"
    # )
    llm = Anthropic(model="claude-3-opus-20240229")
    prompt = txt_2_diagram_prompt_template.format(architecture_plan=requirements_plan)
    resp = str(llm.complete(prompt))
    print(resp)

    
    if resp.count("```")==2:
        resp = extract_code(resp)
    elif resp.count("```") > 0:
        resp = re.sub(r'^.*resp\s*=\s*resp\.replace\("```python",\s*"".*\n?', '', resp, flags=re.MULTILINE)
        resp = resp.replace("```", "")
        
    if isinstance(resp, list):
        if len(resp) >0:
            resp = resp[0]
    
    with open("temp_generated_code.py", "w+") as f:
        f.write(resp)
        
    print(resp)
    
    # search for generated diagram name
    # pattern = r'with Diagram\("([^"]+)"'
    # match = re.search(pattern, resp)
    # if match:
    #     diagram_name = match.group(1) + ".png"
    #     diagram_name = diagram_name.lower().replace(' ', '_')
    #     print(diagram_name)
    # else:
    #     diagram_name = None
    #     print("Diagram name not found\n Code not generated")
    
    # # Execute the generated code to create the diagram
    # try:
    #     if resp and diagram_name:
    #         resp = "from importall import *\n\n" + resp
    #         exec(resp)
    #         diagram_image = Image.open(diagram_name)
    #     else:
    #         diagram_image = None
    #         resp = None
    #         diagram_name = None
    # except Exception as e:
    #     print(f"Error generating diagram: {e}")
    #     diagram_image = None
    
    diagram_name = "output_diagram.png"
    return diagram_name, resp
# 
    
def fix_query(error_str: str):
    """
    Fix import errors in the generated code using a query engine.

    This function takes an error string as input, formats it using a predefined
    prompt template, and queries an index to get a fix for the import error.

    Args:
        error_str (str): The error message string from the failed script execution.

    Returns:
        response (str): The response from the query engine, which should contain the fix for the import error.
    """
    index = LlamaCloudIndex(
    name="import-shema", 
    project_name="Default",
    organization_id="761971b0-20f5-4ea5-967a-f3e0f2e782cf",
    api_key="llx-D9IGGkRCRGVzPK0bbvYpAf0QgVsHiZ8dxSyA3yXrOmTGA1wb"
    )

    query = fix_import_prompt_template.format(error_txt = error_str)
    response = index.as_query_engine().query(query)
    return response

text_to_diagram_tool = FunctionTool.from_defaults(fn=text_to_diagram)
temp_script_tool = FunctionTool.from_defaults(fn=run_script)
import_fixer_tool = FunctionTool.from_defaults(fn=fix_query)

llm  = llm = Anthropic(model="claude-3-opus-20240229")
agent = ReActAgent.from_tools([text_to_diagram_tool, temp_script_tool], llm=llm, verbose=True)

raw_text = """
You are an expert AWS architect, you have two tools 
1. text_to_diagram_tool to generate a solution with best AWS practices
2. temp_script_tool to check if the generated solution code works without no errors
3. If the code has import errors, use the import_fixer_tool to fix the code
4. If the code has errors, fix the errors and generate a new solution
5. If there are no errors exit.


Help me for my following query

I need to deploy an machine learning streamlit application 
it writes output to s3 bucket
it needs 80GB of memory
the scripts run in docker containes

500000 people will use it daily

help me build a aws system architecture
"""

response = agent.chat(raw_text)

print(response)