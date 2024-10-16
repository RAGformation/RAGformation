import pytest
from llama_index.core.prompts import PromptTemplate
from llama_index.core.bridge.pydantic import BaseModel
from typing import List
from llama_index.llms.anthropic import Anthropic
from dotenv import load_dotenv

class MenuItem(BaseModel):
    course_name: str
    is_vegetarian: bool

class Restaurant(BaseModel):
    name: str
    city: str
    cuisine: str
    menu_items: List[MenuItem]

@pytest.fixture
def llm():
    load_dotenv()
    return Anthropic("claude-3-sonnet-20240229")

@pytest.fixture
def prompt_template():
    return PromptTemplate("Generate a restaurant in a given city {city_name}")

def test_restaurant_generation(llm, prompt_template):
    """
    Test to check if Anthropic LLM integration with LlamaIndex works correctly.
    This test verifies that the LLM can generate a structured Restaurant object
    based on a given prompt template.
    """
    restaurant_obj = (
        llm.as_structured_llm(Restaurant)
        .complete(prompt_template.format(city_name="Miami"))
        .raw
    )

    assert isinstance(restaurant_obj, Restaurant)
    assert restaurant_obj.city == "Miami"
    assert restaurant_obj.name
    assert restaurant_obj.cuisine
    assert isinstance(restaurant_obj.menu_items, list)
    assert all(isinstance(item, MenuItem) for item in restaurant_obj.menu_items)
