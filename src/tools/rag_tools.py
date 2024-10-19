from typing import Dict, Any
import sys
sys.path.append("..")
from raw_tool_fuctions.rag_tools import find_similar_blogs


def search_rag(text: str, *args, **kwargs) -> str:
    """
    Perform a RAG (Retrieval-Augmented Generation) search using the provided text.
    
    Args:
    text (str): The text to use for the RAG search.
    
    Returns:
    str: The results of the RAG search.
    """
    print(f"In RAG tool, getting ctx, text is {text}")
    ctx = kwargs.get('context')
    
    print(f"Performing a search from text: {text}")
    response = find_similar_blogs(text)
    print(response)
    
    ctx.data["rag_search_response"] = (
        f"### User query: \n {text}\n ### Results from RAG:\n {response}"
    )
    return response