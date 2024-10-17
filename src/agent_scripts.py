from llama_index.core.tools import FunctionTool
import requests
from typing import Optional
import os
from together import Together
from prompts import txt_2_diagram_prompt_template
from PIL import Image
from llama_index.llms.openai import OpenAI
from llama_index.llms.together import TogetherLLM
from llama_index.llms.anthropic import Anthropic

import openai
import re


from dotenv import load_dotenv
load_dotenv()


client = openai.OpenAI(
  api_key=os.environ.get("TOGETHER_API_KEY"),
  base_url="https://api.together.xyz/v1",
)
def get_code_completion(messages, max_tokens=512, model="codellama/CodeLlama-70b-Instruct-hf"):
    chat_completion = client.chat.completions.create(
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        stop=[
            "<step>"
        ],
        frequency_penalty=1,
        presence_penalty=1,
        top_p=0.7,
        n=10,
        temperature=0.7,
    )
 
    return chat_completion

def extract_code(text):
    # Pattern to match code blocks with or without language specification
    pattern = r'```(?:python)?\s*([\s\S]*?)\s*```'
    
    matches = re.findall(pattern, text, re.MULTILINE)
    return matches
    
    # text = text.replace("```python", "")
    # text = text.replace("```", "")
    # return text

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
        
    # print(resp)
    
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
    
    # Execute the generated code to create the diagram
    try:
        if resp:
            exec(resp)
            # diagram_image = Image.open(diagram_name)
        else:
            diagram_image = None
            resp = None
            diagram_name = None
    except Exception as e:
        print(f"Error generating diagram: {e}")
        diagram_image = None
        return "Error generating diagram: {e}"
    
    diagram_name = "output_diagram.png"
    return "Diagram generated successfully."

    
    # messages = txt_2_diagram_prompt_template.format_messages(architecture_plan=requirements_plan)
     
    # chat_completion = get_code_completion(messages)
                
    # print(chat_completion.choices[0].message.content)



# # Create FunctionTools
# image_to_text_tool = FunctionTool.from_defaults(
#     image_to_text,
#     name="ImageToTextTool",
#     description="Converts an image to text using an API call. Input should be an image URL."
# )

# text_to_diagram_tool = FunctionTool.from_defaults(
#     text_to_diagram,
#     name="TextToDiagramTool",
#     description="Calls text_to_diagram() to generate an AWS architecture code along with a corresponding visual diagram using the Diagrams Python library."
# )

# Example usage
# tools = [image_to_text_tool, text_to_image_tool]

# client = Together()

# getDescriptionPrompt = "You are a UX/UI designer. Describe the attached screenshot or UI mockup in detail. I will feed in the output you give me to a coding model that will attempt to recreate this mockup, so please think step by step and describe the UI in detail. Pay close attention to background color, text color, font size, font family, padding, margin, border, etc. Match the colors and sizes exactly. Make sure to mention every part of the screenshot including any headers, footers, etc. Use the exact text from the screenshot."

# imageUrl = "https://napkinsdev.s3.us-east-1.amazonaws.com/next-s3-uploads/d96a3145-472d-423a-8b79-bca3ad7978dd/trello-board.png"


# stream = client.chat.completions.create(
#     model="meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
#     messages=[
#         {
#             "role": "user",
#             "content": [
#                 {"type": "text", "text": getDescriptionPrompt},
#                 {
#                     "type": "image_url",
#                     "image_url": {
#                         "url": imageUrl,
#                     },
#                 },
#             ],
#         }
#     ],
#     stream=False,
# )

# for chunk in stream:
#     if "choices" in chunk:
#         print(chunk["choices"][0]["delta"]["content"] or "", end="", flush=True)


# st = """
# AWS lambda connected to S3 bucket.
# Don't forget to include the imports.
# """

# text_to_diagram(st)

if __name__ == "__main__":
    user_query = """
Help me build an AWS system architecture for your machine learning Streamlit application that writes output to an S3 bucket, requires 80GB of memory, runs in Docker containers, and is expected to handle 500,000 daily users, you can follow these guidelines:\n\n1. **Compute Resources**:\n   - **Amazon ECS or EKS**: Use Amazon Elastic Container Service (ECS) or Amazon Elastic Kubernetes Service (EKS) to manage your Docker containers. Both services can scale to meet demand and can handle the orchestration of your containers.\n   - **EC2 Instances**: Choose EC2 instances with sufficient memory to support your application. For 80GB of memory, consider using memory-optimized instance types such as the R5 or R6g series. You can also use EC2 Auto Scaling to dynamically adjust the number of instances based on traffic.\n\n2. **Load Balancing**:\n   - **Amazon Application Load Balancer (ALB)**: Use an ALB to distribute incoming traffic across your ECS or EKS instances. This will help manage the load and ensure high availability.\n\n3. **Storage**:\n   - **Amazon S3**: Use S3 for storing the output of your application. S3 is highly durable and scalable, making it suitable for handling large amounts of data generated by your application.\n\n4. **Database**:\n   - Depending on your application's needs, you may require a database to store user data or application state. Consider using Amazon RDS (for relational databases) or Amazon DynamoDB (for NoSQL databases) based on your requirements.\n\n5. **Caching**:\n   - **Amazon ElastiCache**: To improve performance and reduce latency, consider using ElastiCache (Redis or Memcached) to cache frequently accessed data.\n\n6. **Monitoring and Logging**:\n   - **Amazon CloudWatch**: Use CloudWatch for monitoring your application’s performance and logging. Set up alarms to notify you of any issues.\n\n7. **Security**:\n   - Implement AWS Identity and Access Management (IAM) roles and policies to control access to your resources.\n   - Use AWS Key Management Service (KMS) for encrypting sensitive data stored in S3 or databases.\n\n8. **Scaling**:\n   - Implement Auto Scaling for your ECS or EKS clusters to automatically adjust the number of running containers based on the load.\n\n9. **Content Delivery**:\n   - **Amazon CloudFront**: Use CloudFront as a Content Delivery Network (CDN) to cache and deliver your application content closer to users, improving load times.\n\n10. **Cost Management**:\n    - Use AWS Budgets and Cost Explorer to monitor and manage your costs effectively.\n\nHere’s a high-level architecture diagram:\n\n```\n[Users] --> [CloudFront] --> [Application Load Balancer] --> [ECS/EKS Cluster] --> [S3 Bucket]\n                                      |\n                                      --> [ElastiCache]\n                                      |\n                                      --> [RDS/DynamoDB]\n```\n\nThis architecture will help you efficiently deploy your Streamlit application on AWS while ensuring scalability, performance, and security. If you have any specific requirements or need further details on any component, feel free to ask
  """
    
    text_to_diagram(user_query)
    