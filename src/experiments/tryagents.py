from llama_index.core.agent import FunctionCallingAgentWorker
from llama_index.core.tools import FunctionTool
from llama_index.utils.workflow import draw_all_possible_flows
from typing import Optional, List, Callable
from colorama import Fore, Style
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.openai import OpenAI
from llama_index.llms.ollama import Ollama
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.groq import Groq
from llama_index.agent.openai import OpenAIAgent
from llama_index.core.agent.legacy.react.base import ReActAgent
from llama_index.core.agent import AgentRunner
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from prompts import txt_2_diagram_prompt_template, fix_import_prompt_template, fix_and_write_code_template
import subprocess

from agent_scripts import text_to_diagram

from events import InitializeEvent, ConciergeEvent, OrchestratorEvent, PriceLookupEvent, ImageToTextEvent, TextToDiagramEvent, TextToRAGEvent, ReporterEvent, FixImportEvent, ArchitectureCheckEvent

import dotenv
dotenv.load_dotenv()

from llama_index.core.workflow import (
    step,
    Context,
    Workflow,
    Event,
    StartEvent,
    StopEvent
)
class ConciergeWorkflow(Workflow):
    @staticmethod
    def log_history(ctx: Context, agent: str, role: str, content: str):

        # TODO: log system prompts (on first call)
        # TODO: log assistant responses
        ctx.data["history"][agent].append({
            "role": role,
            "content": content,
        })

    @step
    async def concierge(self, ctx: Context, ev: StartEvent) -> ConciergeEvent | OrchestratorEvent | StopEvent:
        system_prompt = """
        You are a helpful assistant that is helping a user navigate an automatic architecture diagram assistant.
        Your job is to ask the user questions to figure out what they want to do, and give them the available things they can do.
        That includes:
        * receiving the description of a system
        * draw a diagram from a description
        * verifying if the diagram code is correct
        * verifying if the architecture diagram resource positioning is correct
        * looking up the price of a service     
        * generate a report
        You should start by listing the things you can help them do.            
        """
        
        if "concierge_agent" not in ctx.data:
            ctx.data["concierge_agent"] = FunctionCallingAgentWorker.from_tools(
                tools=[],
                llm=self.llm,
                allow_parallel_tool_calls=False,
                system_prompt=system_prompt
            ).as_agent()

        concierge_agent = ctx.data["concierge_agent"]
        
        if ev.just_completed:
            user_msg = f"FYI, the user has just completed the task: {ev.just_completed}"
        elif ev.need_help:
            return OrchestratorEvent(request=ev.request)
        elif ev.request:
            user_msg = ev.request
        else:
            user_msg = "Hello!"

        self.concierge_memory.put(ChatMessage(role="user", content=user_msg))
        chat_history = self.concierge_memory.get()
        
        # Convert chat history to a string format that the agent can understand
        chat_string = "\n".join([f"{msg.role}: {msg.content}" for msg in chat_history])
        
        response = await concierge_agent.achat(chat_string)
        self.concierge_memory.put(ChatMessage(role="assistant", content=response.response))

        print(f"Concierge: {response.response}")
        user_input = input("> ").strip()
        
        if user_input.lower() in ["exit", "quit", "bye"]:
            return StopEvent()
        
        return OrchestratorEvent(request=user_input)

    @step
    async def orchestrator(self, ctx: Context, ev: OrchestratorEvent) -> ConciergeEvent | StopEvent:
        if "orchestrator_agent" not in ctx.data:
            ctx.data["orchestrator_agent"] = FunctionCallingAgentWorker.from_tools(
                tools=self.tools,
                llm=self.llm,
                allow_parallel_tool_calls=False,
            ).as_agent()

        orchestrator_agent = ctx.data["orchestrator_agent"]
        
        self.orchestrator_memory.put(ChatMessage(role="user", content=ev.request))
        chat_history = self.orchestrator_memory.get()
        
        # Convert chat history to a string format that the agent can understand
        chat_string = "\n".join([f"{msg.role}: {msg.content}" for msg in chat_history])
        
        response = await orchestrator_agent.achat(chat_string)
        self.orchestrator_memory.put(ChatMessage(role="assistant", content=response.response))

        print(f"Orchestrator: {response.response}")
        
        # Check if any tools were called
        if response.tool_calls:
            for tool_call in response.tool_calls:
                print(f"Tool {tool_call.tool_name} called with args: {tool_call.tool_kwargs}")
                tool = next((t for t in self.tools if t.metadata.name == tool_call.tool_name), None)
                if tool:
                    tool_output = await tool(**tool_call.tool_kwargs)
                    print(f"Tool {tool_call.tool_name} output: {tool_output}")
            
            # After tool execution, we loop back to the orchestrator
            return OrchestratorEvent(request="Continue with the previous task.")
        
        # If no tools were called, we return to the concierge
        return ConciergeEvent(just_completed="orchestrator task")

async def main():
    workflow = ConciergeWorkflow(timeout=1200, verbose=True)
    result = await workflow.run()
    print("Workflow completed:", result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())