from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.openai import OpenAI
from llama_index.llms.ollama import Ollama
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.groq import Groq


def initialize_llm(llm_type: str):
    """
    Initialize and return a language model based on the given type.

    Args:
    llm_type (str): The type of language model to initialize.

    Returns:
    An instance of the specified language model.

    Raises:
    ValueError: If an unsupported LLM type is provided.
    """
    llm_map = {
        "AzureOpenAI": lambda: AzureOpenAI(
            engine="testing-first-gbu-doc", model="gpt-4o", temperature=0.4
        ),
        "Ollama": lambda: Ollama(model="llama3.1:8b", request_timeout=120.0),
        "OpenAI": lambda: OpenAI(model="gpt-4o", temperature=0.8),
        "Anthropic": lambda: Anthropic(model="claude-3-opus-20240229", temperature=0.4),
        "Groq": lambda: Groq(model="llama3-70b-8192", temperature=0.8),
    }

    if llm_type not in llm_map:
        raise ValueError(f"Unsupported LLM type: {llm_type}")

    return llm_map[llm_type]()
