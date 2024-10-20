from llama_index.core.tools import FunctionTool
import requests
from typing import Optional
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/")))
# sys.path.append("../..")
import os
from together import Together
from prompts import txt_2_diagram_prompt_template, fix_import_prompt_template
from PIL import Image
from llama_index.llms.openai import OpenAI
from llama_index.llms.together import TogetherLLM
from llama_index.llms.anthropic import Anthropic
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex

import openai
import re
import config


def find_similar_blogs(query: str) -> str:
    """
    Find and retrieve similar blog content based on the provided query.

    This function uses a LlamaCloudIndex to perform a search for blogs that are similar
    to the given query. It initializes the index with the necessary configuration and
    queries the chat engine to get relevant results.

    Args:
        query (str): The query snippet for which similar blogs are to be found.

    Returns:
        str: The response from the chat engine containing similar blog content.
    """
    print(f"Checking syntax for the provided query")
    index = LlamaCloudIndex(
        name="ragathon-test",
        project_name="Default",
        organization_id=config.PINECONE_ORGANIZATION_ID,
        api_key=config.PINECONE_API_KEY,
    )

    response = index.as_chat_engine().chat(query)
    return str(response)


if __name__ == "__main__":
    pass
