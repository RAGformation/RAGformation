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

# Centralize LLM initialization
def initialize_llm(llm_type: str):
    llm_map = {
        "AzureOpenAI": lambda: AzureOpenAI(engine="testing-first-gbu-doc", model="gpt-4o", temperature=0.4),
        "Ollama": lambda: Ollama(model="llama3.1:8b", request_timeout=120.0),
        "OpenAI": lambda:  OpenAI(model="gpt-4o",temperature=0.8),
        "Anthropic": lambda: Anthropic(model="claude-3-opus-20240229", temperature=0.4),
        "Groq": lambda: Groq(model="llama3-70b-8192", temperature=0.8),
    }
    return llm_map.get(llm_type, lambda: None)()

class ConciergeWorkflow(Workflow):

    @staticmethod
    def log_history(ctx: Context, agent: str, role: str, content: str):

        # TODO: log system prompts (on first call)
        # TODO: log assistant responses
        ctx.data["history"][agent].append({
            "role": role,
            "content": content,
        })

    @step(pass_context=True)
    async def initialize(self, ctx: Context, ev: InitializeEvent) -> ConciergeEvent:
        ctx.data.update({
            "user": {"username": None, "session_token": None, "account_id": None},
            "success": None,
            "redirecting": None,
            "overall_request": None,
            "history": {agent: [] for agent in ["image_to_text", "text_to_diagram", "text_to_rag", "report", "price_lookup", "fix_import", "architecture_check"]},
            "diagram_syntax_error": None,
            "diagram_node_arrangement_error": None,
            "requirements": None,
            "flow_confirmed": False,
            "llm": initialize_llm("OpenAI")
        })
        return ConciergeEvent()

    @step(pass_context=True)
    async def concierge(self, ctx: Context, ev: ConciergeEvent | StartEvent) -> InitializeEvent | StopEvent | OrchestratorEvent:
        if "user" not in ctx.data:
            return InitializeEvent()

        if "concierge" not in ctx.data:
            system_prompt = """
            You are a helpful assistant that is helping a user navigate an automatic architecture diagram assistant
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
            # system_prompt = PromptTemplate(system_prompt)
            
            # ctx.data["concierge"] = OpenAIAgent.from_tools(
            #     tools=[],
            #     llm=ctx.data["llm"],
            #     allow_parallel_tool_calls=False,
            #     system_prompt=system_prompt
            # )
            
            
            ctx.data["concierge"] = FunctionCallingAgentWorker.from_tools(
                tools=[],  # <-- This is likely the cause of the error
                llm=ctx.data["llm"],
                allow_parallel_tool_calls=False,
                system_prompt=system_prompt
            ).as_agent()
            
            # agent = ReActAgent.from_tools(
            #     [], 
            #     llm=Groq(model="llama3-70b-8192", temperature=0.8) 
            #     verbose=True
            # )
            # ctx.data["concierge"] = agent

        concierge = ctx.data["concierge"]
        if ctx.data["overall_request"]:
            last_request = ctx.data["overall_request"]
            ctx.data["overall_request"] = None
            return OrchestratorEvent(request=last_request)
        elif ev.just_completed:
            response = concierge.chat(f"FYI, the user has just completed the task: {ev.just_completed}")
        elif ev.need_help:
            return OrchestratorEvent(request=ev.request)
        else:
            response = concierge.chat("Hello!")

        print(Fore.MAGENTA + str(response) + Style.RESET_ALL)
        user_msg_str = input("> ").strip()
        return OrchestratorEvent(request=user_msg_str)

    @step(pass_context=True)
    async def orchestrator(self, ctx: Context, ev: OrchestratorEvent) -> ConciergeEvent| OrchestratorEvent | StopEvent :
        print(f"Orchestrator received request: {ev.request}")
        def run_and_check_syntax() -> str:
            """Run the file `temp_generated_code.py` if it runs successfully, the syntax is correct otherwise return the error."""
            try:
                result = subprocess.run(['/Users/bread/Documents/RAGformation/.venv/bin/python', 'temp_generated_code.py'], capture_output=True, text=True)
                if result.returncode == 0:
                    ctx['diagram_syntax_error'] = None
                    return "Syntax is correct."
                else:
                    ctx['diagram_syntax_error'] = f"Error encountered: {result.stderr}"
                    return f"Error encountered: {result.stderr}"
            except Exception as e:
                return f"Exception occurred: {str(e)}"

        def suggest_imports(code: str) -> str:
            """If the diagram generation throws an error, use this tool to fix the imports"""
            print(f"Checking syntax for the provided code")
            if ctx['diagram_syntax_error'] is not None:
                index = LlamaCloudIndex(
                name="import-shema", 
                project_name="Default",
                organization_id=os.environ["PINECONE_API_KEY"],
                api_key=os.environ["PINECONE_ORGANIZATION_ID"]
                )

                query = fix_import_prompt_template.format(error_txt = code)
                response = index.as_query_engine().query(query)
                return f"The correct import should be {response}"
            else:
                return f"There are no import errors"

        def write_to_file(content: str, filename: str = "temp_generated_code.py") -> str:
            """Write the given content to a file."""
            try:
                with open(filename, 'w') as file:
                    file.write(content)
                return f"Content written to {filename} successfully."
            except Exception as e:
                return f"Failed to write to file: {str(e)}"

        def fix_and_write_code(input_filename: str = "temp_generated_code.py", output_filename: str = "temp_generated_code.py") -> str:
            """Read code from a file, fix it using LLM, and write the fixed code to another file."""
            try:
                with open(input_filename, 'r') as file:
                    original_code = file.read()

                error_message = ctx.get('diagram_syntax_error', 'No errors.')
                
                llm = Anthropic(model="claude-3-opus-20240229")
                prompt = fix_and_write_code_template.format(original_code=original_code, error_message=error_message)
                resp = str(llm.complete(prompt))

                # Write the fixed code to the output file
                write_result = write_to_file(str(resp), output_filename)

                return f"Code fixed and written to {output_filename}."
            except Exception as e:
                return f"Failed to fix and write code: {str(e)}"
            
        def generate_diagram(text: str) -> str:
            """Use this to generate aws solution diagram from text """
            resp = text_to_diagram(text)
            
            if "successful" in resp.lower():
                return "Output diagram saved to output_diagram.png"
            else:
                return f"Encountered error: {resp}"
            

        # system_prompt = f"""
        # You are an advanced programming assistant specializing in checking and fixing the syntax of Python code. Follow these steps in order:
        # ## 1. Initial Syntax Check
        # - Use the `run_and_check_syntax` tool to execute temp_generated_code.py python file
        # - If the code runs without errors, conclude that there are no syntax issues
        # - If errors are encountered, proceed to step 2

        # ## 2. Error Handling and Logging
        # - If syntax errors are detected:
        # - Use the `suggest_imports` tool to get the suggested imports for import errors.
        # - Use the `fix_and_write_code` tool to rewrite new code and save.

        # ## 3. Verification
        # - After applying fixes, rerun the `run_and_check_syntax` tool to verify that all syntax issues have been resolved
        # - If errors persist, repeat steps 2-3 as necessary
        # - Once new code is written, ask the `text_to_diagram` tool to regenerate the drawing.
        
        # Once you have completed fixing new code, you *must* call the tool named "done" to signal that you are done. Do this before you respond.
        # If you don't know what to do call need_help.
        # """

        tools = [
            FunctionTool.from_defaults(fn=run_and_check_syntax),
            FunctionTool.from_defaults(fn=suggest_imports),
            FunctionTool.from_defaults(fn=fix_and_write_code),
            FunctionTool.from_defaults(fn=generate_diagram)
        ]
        
        if "orchestrator" not in ctx.data:
            ctx.data["orchestrator"] = FunctionCallingAgentWorker.from_tools(
                tools=tools,
                llm=ctx.data["llm"],
                allow_parallel_tool_calls=False,
                # system_prompt=system_prompt
            ).as_agent()

        response = str(ctx.data["orchestrator"].chat(ev.request))
        print(response)

        if response == "FAILED":
            print("Orchestration agent failed to return a valid speaker; try again")
            return OrchestratorEvent(request=ev.request)
        else:
            return ConciergeEvent(request=ev.request)

                

class ConciergeAgent:
    name: str
    parent: Workflow
    tools: list[FunctionTool]
    system_prompt: str
    context: Context
    current_event: Event
    trigger_event: Event

    def __init__(
            self,
            parent: Workflow,
            tools: List[Callable],
            system_prompt: str,
            trigger_event: Event,
            context: Context,
            name: str,
    ):
        self.name = name
        self.parent = parent
        self.context = context
        self.system_prompt = system_prompt
        self.context.data["redirecting"] = False
        self.trigger_event = trigger_event

        # set up the tools including the ones everybody gets
        def done() -> None:
            """When you complete your task, call this tool."""
            print(f"{self.name} is complete")
            self.context.data["redirecting"] = True
            parent.send_event(ConciergeEvent(just_completed=self.name))

        def need_help() -> None:
            """If the user asks to do something you don't know how to do, call this."""
            print(f"{self.name} needs help")
            self.context.data["redirecting"] = True
            parent.send_event(ConciergeEvent(request=self.current_event.request,need_help=True))

        self.tools = [
            FunctionTool.from_defaults(fn=done),
            FunctionTool.from_defaults(fn=need_help)
        ]
        for t in tools:
            self.tools.append(FunctionTool.from_defaults(fn=t))

        agent_worker = FunctionCallingAgentWorker.from_tools(
            self.tools,
            llm=self.context.data["llm"],
            allow_parallel_tool_calls=False,
            system_prompt=self.system_prompt
        )
        self.agent = agent_worker.as_agent()

    def handle_event(self, ev: Event):
        self.current_event = ev

        response = str(self.agent.chat(ev.request))
        print(Fore.MAGENTA + str(response) + Style.RESET_ALL)

        # if they're sending us elsewhere we're done here
        if self.context.data["redirecting"]:
            self.context.data["redirecting"] = False
            return None

        # otherwise, get some user input and then loop
        user_msg_str = input("> ").strip()
        return self.trigger_event(request=user_msg_str)

draw_all_possible_flows(ConciergeWorkflow, filename="concierge_flows.html")



async def main():
    c = ConciergeWorkflow(timeout=1200, verbose=True)
    result = await c.run()
    print(result)

# Check if an event loop is already running
if __name__ == "__main__":
    import asyncio
    try:
        # If there's no running event loop, use asyncio.run()
        if not asyncio.get_event_loop().is_running():
            asyncio.run(main())
        else:
            # If an event loop is running, use await
            try:
                # await main()  # For Jupyter uncomment this
                pass
            except Exception as e:
                print(e)
    except RuntimeError:
        # For environments like Jupyter that may raise errors for nested event loops
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.run(main())

