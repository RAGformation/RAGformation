from llama_index.core.tools import FunctionTool
import requests
from typing import Optional
import os
from together import Together
from prompts import txt_2_diagram_prompt_template, fix_import_prompt_template
from PIL import Image
from llama_index.llms.openai import OpenAI
from llama_index.llms.together import TogetherLLM
from llama_index.llms.anthropic import Anthropic
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
import sys
import subprocess
from llama_index.llms.openai import OpenAI
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from typing import Dict, Any, List

import openai
import re
import config

def write_to_file(content: str, filename: str = "temp_generated_code.py") -> str:
    """Write the given content to a file."""
    try:
        with open(filename, 'w') as file:
            file.write(content)
        return f"Content written to {filename} successfully."
    except Exception as e:
        return f"Failed to write to file: {str(e)}"

def extract_code(text):
    # Pattern to match code blocks with or without language specification
    pattern = r'```(?:python)?\s*([\s\S]*?)\s*```'
    matches = re.findall(pattern, text, re.MULTILINE)
    return matches

def image_to_text(image_url: str) -> str:
    """
    Convert an image to text using an API call.
    
    Args:
        image_url (str): The URL of the image to be converted to text.
    
    Returns:
        str: The text extracted from the image.
    """
    # This is a placeholder for the actual API call
    # You would replace this with your actual API implementation
    response = requests.post(
        "https://api.example.com/image-to-text",
        json={"image_url": image_url}
    )
    return response.json()["text"]

def text_to_diagram(requirements_plan: str) -> str:
    """
    Automatically generates AWS architecture code and a corresponding visual diagram using the Diagrams Python library.
    
    Args:
        requirements_plan (str): A detailed description of the requirements for the AWS architecture.
    
    Returns:
        If the diagram generation was successful or failure
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

    try:
        if resp:
            exec(resp)
        else:
            diagram_image = None
            resp = None
            diagram_name = None
    except Exception as e:
        print(f"Error generating diagram: {e}")
        diagram_image = None
        return "Error generating diagram: {e}"
    
    return "Diagram generated successfully."

def _run_and_check_syntax() -> str:
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

def _suggest_imports() -> str:
    """
    Suggest correct imports based on the error message.
    
    Args:
    ctx (Dict[str, Any]): The context containing the current state and data.
    
    Returns:
    str: The error message or suggested imports.
    """
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

def _fix_and_write_code() -> str:
    """
    Fix errors in the code and write the corrected code to a file.
    
    Args:
    ctx (Dict[str, Any]): The context containing the current state and data.
    
    Returns:
    str: A message indicating the result of the operation.
    """

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

def _generate_diagram() -> str:
    """
    Generate a diagram based on the text description in the context.
    
    Args:
    ctx (Dict[str, Any]): The context containing the current state and data.
    
    Returns:
    str: A message indicating the result of the diagram generation.
    """
    print("Generating diagram...")

    text = ctx.data['history']
    print(f"Generating diagram query: {text}")
    
    resp = text_to_diagram(text)
    print(f"Generating diagram response: {resp}")

    if "successfully" in resp.lower():
        ctx.data["diagram_syntax_error"] = None
        response = "Output diagram saved to output_diagram.png"
    else:
        ctx.data["diagram_syntax_error"] = f"Error encountered: {resp}"
        response = f"Error encountered: {resp}"
    ctx.data['query'] += f"\n\n{response}"
    return ctx.data['query']

if __name__ == "__main__":
    user_query = """
    Help me build an AWS system architecture for your machine learning Streamlit application that writes output to an S3 bucket, requires 80GB of memory, runs in Docker containers, and is expected to handle 500,000 daily users, you can follow these guidelines:\n\n1. **Compute Resources**:\n   - **Amazon ECS or EKS**: Use Amazon Elastic Container Service (ECS) or Amazon Elastic Kubernetes Service (EKS) to manage your Docker containers. Both services can scale to meet demand and can handle the orchestration of your containers.\n   - **EC2 Instances**: Choose EC2 instances with sufficient memory to support your application. For 80GB of memory, consider using memory-optimized instance types such as the R5 or R6g series. You can also use EC2 Auto Scaling to dynamically adjust the number of instances based on traffic.\n\n2. **Load Balancing**:\n   - **Amazon Application Load Balancer (ALB)**: Use an ALB to distribute incoming traffic across your ECS or EKS instances. This will help manage the load and ensure high availability.\n\n3. **Storage**:\n   - **Amazon S3**: Use S3 for storing the output of your application. S3 is highly durable and scalable, making it suitable for handling large amounts of data generated by your application.\n\n4. **Database**:\n   - Depending on your application's needs, you may require a database to store user data or application state. Consider using Amazon RDS (for relational databases) or Amazon DynamoDB (for NoSQL databases) based on your requirements.\n\n5. **Caching**:\n   - **Amazon ElastiCache**: To improve performance and reduce latency, consider using ElastiCache (Redis or Memcached) to cache frequently accessed data.\n\n6. **Monitoring and Logging**:\n   - **Amazon CloudWatch**: Use CloudWatch for monitoring your application’s performance and logging. Set up alarms to notify you of any issues.\n\n7. **Security**:\n   - Implement AWS Identity and Access Management (IAM) roles and policies to control access to your resources.\n   - Use AWS Key Management Service (KMS) for encrypting sensitive data stored in S3 or databases.\n\n8. **Scaling**:\n   - Implement Auto Scaling for your ECS or EKS clusters to automatically adjust the number of running containers based on the load.\n\n9. **Content Delivery**:\n   - **Amazon CloudFront**: Use CloudFront as a Content Delivery Network (CDN) to cache and deliver your application content closer to users, improving load times.\n\n10. **Cost Management**:\n    - Use AWS Budgets and Cost Explorer to monitor and manage your costs effectively.\n\nHere’s a high-level architecture diagram:\n\n```\n[Users] --> [CloudFront] --> [Application Load Balancer] --> [ECS/EKS Cluster] --> [S3 Bucket]\n                                      |\n                                      --> [ElastiCache]\n                                      |\n                                      --> [RDS/DynamoDB]\n```\n\nThis architecture will help you efficiently deploy your Streamlit application on AWS while ensuring scalability, performance, and security. If you have any specific requirements or need further details on any component, feel free to ask
    """
    
    text_to_diagram(user_query)
    