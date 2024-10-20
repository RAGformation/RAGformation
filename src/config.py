import os
from dotenv import load_dotenv
load_dotenv()

# Python interpreter path
PYTHON_PATH = ""

# LlamaCloud configuration
PINECONE_ORGANIZATION_ID = ""
PINECONE_API_KEY = ""

# LLM configuration
DEFAULT_LLM_TYPE = "OpenAI"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FILE = "concierge_workflow.log"

# File paths
TEMP_CODE_FILE = "temp_generated_code.py"
OUTPUT_DIAGRAM_FILE = "output_diagram.png"
