import os
from typing import List
from openai import OpenAI
from toolhouse import Toolhouse
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
th = Toolhouse(access_token=os.environ["TOOLHOUSE_KEY"], provider="openai")

MODEL = 'gpt-4o-mini'

messages = [{
    "role": "user",
    "content":
        """
        Run the code below and give output
        ```
        x = 6
        print(x
        ```
        """
}]

response = client.chat.completions.create(
  model=MODEL,
  messages=messages,
  tools=th.get_tools()
)

messages += th.run_tools(response)
print(messages)