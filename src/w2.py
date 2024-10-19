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
from prompts import fix_import_prompt_template, fix_and_write_code_template


from agent_scripts import text_to_diagram as draw_text_to_diagram

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
    async def orchestrator(self, ctx: Context, ev: OrchestratorEvent) -> ConciergeEvent  | PriceLookupEvent | ImageToTextEvent | TextToDiagramEvent | TextToRAGEvent | ArchitectureCheckEvent| FixImportEvent| ReporterEvent | StopEvent:
        
        print(f"Orchestrator received request: {ev.request}")
        
        def emit_text_to_diagram() -> bool:
            """Call this if the user wants to text to diagram"""
            print("__emitted: text to diagram")
            self.send_event(TextToDiagramEvent(request=ev.request))
            return True

        def emit_concierge() -> bool:
            """Call this if the user wishes to perform another action, or if you’re unsure of their intent. You can also call this to prompt a response from the user.​"""
            print("__emitted: concierge")
            self.send_event(ConciergeEvent(request=ev.request))
            return True

        def emit_stop() -> bool:
            """Call this if the user wants to stop or exit the system."""
            print("__emitted: stop")
            self.send_event(StopEvent())
            return True

        def emit_price_lookup() -> bool:
            """Call this if the user wants to look up a price"""
            print("__emitted: price lookup")
            self.send_event(PriceLookupEvent(request=ev.request))
            return True

        def emit_text_to_rag() -> bool:
            """Call this if the user wants to perform a text to RAG search"""
            print("__emitted: text to rag")
            self.send_event(TextToRAGEvent(request=ev.request))
            return True

        def emit_report() -> bool:
            """Call this if the user wants to generate a report"""
            print("__emitted: report")
            self.send_event(ReporterEvent(request=ev.request))
            return True

        tools = [
            FunctionTool.from_defaults(fn=emit_concierge),
            FunctionTool.from_defaults(fn=emit_text_to_diagram),
            FunctionTool.from_defaults(fn=emit_stop),
            FunctionTool.from_defaults(fn=emit_price_lookup),
            FunctionTool.from_defaults(fn=emit_text_to_rag),
            FunctionTool.from_defaults(fn=emit_report)
        ]
        
        
        # ! ToDo does not work
        # def create_emit_function(event_class):
        #     def emit():
        #         print(f"__emitted: {event_class.__name__.lower().replace('event', '')}")
        #         event = event_class(request=ev.request)
        #         self.send_event(event)
        #         return True
        #     return emit
        
        # event_classes = [
        #     PriceLookupEvent,
        #     ImageToTextEvent,
        #     TextToDiagramEvent,
        #     TextToRAGEvent,
        #     ReporterEvent,
        #     ConciergeEvent,
        #     StopEvent
        # ]
        # tools = [
        #     FunctionTool.from_defaults(
        #         fn=create_emit_function(event_class),
        #         name=f"emit_{event_class.__name__.lower().replace('event', '')}",
        #         description=f"Call this if the user wants to {event_class.__name__.lower().replace('event', '')}"
        #     )
        #     for event_class in event_classes
        # ]

        system_prompt = """
        You are an advanced orchestrator agent with the following capabilities and responsibilities:
        ## 1. Requirements Gathering and Enhancement
        - Receive initial requirements from users
        - Utilize the `text_to_rag` tool to refine and enhance the requirements
        - If the tool indicates that the requirements are complete, proceed directly to generating the architecture diagram
        - Otherwise, present the enhanced requirements to users for approval or further refinement
        - Iterate on the requirements gathering process until user approval is obtained

        ## 2. Diagram Generation
        - Forward approved requirements to the `text_to_diagram` tool
        - Generate diagrams based on the provided requirements
        - If diagram generation encounters an error:
        - Call the `fix_import` tool
        - Apply the suggested changes
        - Use the `text_to_diagram` tool again to redraw the diagram
        - Present the resulting diagrams to users for review
        
        ## 3. Error fixing
        - If there is error forward requests to the `fix_import` tool.
        - If you want to test the results generated from `text_to_diagram` asj the `fix_import` agent to review it.

        ## 3. Tool Usage Guidelines
        - Run an agent by calling the appropriate tool for that agent
        - Call only one tool at a time
        - Do not attempt to determine dependencies between agents; they will handle this internally

        ## 4. Error Handling
        - If no tools are called during the process, return the string "FAILED" (without quotes) and nothing else

        ## 5. User Interaction
        - Maintain clear communication with users throughout the process
        - Seek user approval at key stages (e.g., after requirements enhancement, diagram generation)
        - Be prepared to explain the process and results to users as needed

        """

        if "orchestrator" not in ctx.data:
            ctx.data["orchestrator"] = FunctionCallingAgentWorker.from_tools(
                tools=tools,
                llm=ctx.data["llm"],
                allow_parallel_tool_calls=False,
                system_prompt=system_prompt
            ).as_agent()

        response = str(ctx.data["orchestrator"].chat(ev.request))
        
        print(response)

        if response == "FAILED":
            print("Orchestration agent failed to return a valid speaker; try again")
            return OrchestratorEvent(request=ev.request)

    @step(pass_context=True)
    async def price_lookup(self, ctx: Context, ev: PriceLookupEvent) -> ConciergeEvent:

        print(f"Price Lookup received request: {ev.request}")
        self.log_history(ctx, "price_lookup", "user", ev.request)

        if "price_lookup_agent" not in ctx.data:
            def lookup_price(name: str) -> str:
                """Useful for looking the price of a service."""
                print(f"Looking up price for {name} service")
                return f"Service {name} currently costs $100.00"

            def search_for_service(name: str) -> str:
                """Useful for searching for a service from a free-form description."""
                print("Searching for item or component")
                return name.upper()

            def has_requirements() -> bool:
                """Checks if the user has provided the requirements."""
                print("Price Lookup checking if user has provided the requirements")
                if ctx.data["requirements"] is not None:
                    return True
                else:
                    return False

            def has_confirmed_flow() -> bool:
                """Checks if the user has confirmed the flow."""
                print("Price Lookup checking if user confirmed the flow")
                return ctx.data["requirements"]

            system_prompt = (f"""
                You are a helpful assistant that is looking up service prices.
                The user may not know the name of the service they're interested in,
                so you can help them look it up by a description of what the service does or provides.
                You can only look up names given to you by the search_for_service tool, don't make them up. Trust the output of the search_for_service tool even if it doesn't make sense to you.
                The user can only request a price lookup if they have provided requirements, which you can check with the has_requirements tool.
                The user can only request a price lookup if they have confirmed the flow, which you can check with the flow_confirmed tool.
                Once you have retrieved a price, you *must* call the tool named "done" to signal that you are done. Do this before you respond.
                If the user asks to do anything other than look up a service price, call the tool "need_help" to signal some other agent should help.
            """)

            ctx.data["price_lookup_agent"] = ConciergeAgent(
                name="Price Lookup Agent",
                parent=self,
                tools=[lookup_price, search_for_service, has_requirements, has_confirmed_flow],
                context=ctx,
                system_prompt=system_prompt,    
                trigger_event=PriceLookupEvent
            )

        return ctx.data["price_lookup_agent"].handle_event(ev)

    @step(pass_context=True)
    async def image_to_text(self, ctx: Context, ev: ImageToTextEvent) -> ConciergeEvent:

        print(f"Image to Text received request: {ev.request}")
        self.log_history(ctx, "image_to_text", "user", ev.request)

        if "image_to_text_agent" not in ctx.data:
            def extract_text(image: str) -> str:
                """Useful for extracting text from an image."""
                print(f"Extracting text from image {image}")
                return f"Image {image} contains Lorem ipsum dolor sit amet"

            system_prompt = (f"""
                You are a helpful assistant that extracts text from an image.
                You can only extract text from images given to you by the extract_text tool, don't make them up. Trust the output of the extract_text tool even if it doesn't make sense to you.
                Once you have extracted the text, you *must* call the tool named "done" to signal that you are done. Do this before you respond.
                If the user asks to do anything other than extract text from an image, call the tool "need_help" to signal some other agent should help.
            """)

            ctx.data["image_to_text_agent"] = ConciergeAgent(
                name="Image to Text Agent",
                parent=self,
                tools=[extract_text],
                context=ctx,
                system_prompt=system_prompt,
                trigger_event=ImageToTextEvent
            )

        return ctx.data["image_to_text_agent"].handle_event(ev)
    
    

    @step(pass_context=True)
    async def text_to_diagram(self, ctx: Context, ev: TextToDiagramEvent) -> FixImportEvent | OrchestratorEvent | ConciergeEvent:

        print(f"Text to Diagram received request: {ev.request}")
        self.log_history(ctx, "text_to_diagram", "user", ev.request)

        if "text_to_diagram_agent" not in ctx.data:
            def generate_diagram(text: str) -> str:
                """Useful for describing a diagram using text."""
                resp = draw_text_to_diagram(text)
                
                if "successfully" in resp.lower():
                    ctx['diagram_syntax_error'] = None
                    return "Output diagram saved to output_diagram.png"
                else:
                    ctx['diagram_syntax_error'] = f"Error encountered: {resp}"
                    return f"Error encountered: {resp}"


            system_prompt = (f"""
                You are a specialized AWS assistant designed to generate architecture diagrams from provided text descriptions. Adhere to the following guidelines:
                1. Diagram Generation:
                - Only generate diagrams based on the text provided by the orchestrator.
                - Do not create or invent diagrams without explicit input.
                2. Error Handling:
                - If you encounter an error while generating the diagram, immediately send the error back to the orchestrator.
                - Do not attempt to fix errors yourself.
                3. Task Limitation:
                - Your primary function is to generate AWS architecture diagrams.
                - If the orchestrator requests any task other than diagram generation, use the `need_help` tool to signal that another agent should assist.
                4. Completion Protocol:
                - After successfully generating the diagram, you MUST call the `done` tool to indicate task completion.
                - Always use the `done` tool before providing your final response.
                Remember: Your role is strictly limited to AWS architecture diagram generation based on provided text. For all other requests or tasks, defer to other specialized agents using the `need_help` tool.
            """)

            ctx.data["text_to_diagram_agent"] = ConciergeAgent(
                name="Text to Diagram Agent",
                parent=self,
                tools=[generate_diagram],
                context=ctx,
                system_prompt=system_prompt,
                trigger_event=TextToDiagramEvent
            )

        return ctx.data["text_to_diagram_agent"].handle_event(ev)

    @step(pass_context=True)
    async def text_to_rag(self, ctx: Context, ev: TextToRAGEvent) -> ConciergeEvent:

        print(f"Text to RAG received request: {ev.request}")
        self.log_history(ctx, "text_to_rag", "user", ev.request)

        if "text_to_rag_agent" not in ctx.data:
            def search_rag(text: str) -> str:
                """Useful for requesting a RAG search using text."""
                print(f"Performing a search from text {text}")
                return f"No RAG search required, the solution is 100% good, proceed to draw the architecture."

            system_prompt = (f"""
                You are an efficient assistant specialized in conducting RAG (Retrieval-Augmented Generation) searches. 
                Your role is to use the “search_rag” tool to retrieve relevant information based on the text provided. However, performing the search is optional—if the text already seems well-formed and sufficient, 
                you may simply respond with “This is very good, proceed with the architecture diagram.”
                After completing a search, you must immediately call the “done” tool to indicate the search is finished, before providing any response to the user.
                If the user requests any task unrelated to performing a search, use the “need_help” tool to signal that a different agent should handle the request.
                You are not permitted to generate information or search results on your own; you must rely solely on the output of the “search_rag” tool, even if it seems illogical.
            """)

            ctx.data["text_to_rag_agent"] = ConciergeAgent(
                name="Text to RAG Agent",
                parent=self,
                tools=[search_rag],
                context=ctx,
                system_prompt=system_prompt,
                trigger_event=TextToRAGEvent
            )

        return ctx.data["text_to_rag_agent"].handle_event(ev)

    @step(pass_context=True)
    async def report(self, ctx: Context, ev: ReporterEvent) -> ConciergeEvent:

        print(f"Report received request: {ev.request}")
        self.log_history(ctx, "report", "user", ev.request)

        if "report_agent" not in ctx.data:
            def report() -> str:
                """Useful for generating a report."""
                print(f"Generating report from text")
                return f"Report generated"

            system_prompt = (f"""
                You are a helpful assistant that generates a report.
                You can only generate a report by the report tool, don't make them up. Trust the output of the report tool even if it doesn't make sense to you.
                Once you have performed the search, you *must* call the tool named "done" to signal that you are done. Do this before you respond.
                If the user asks to do anything other than generate a search, call the tool "need_help" to signal some other agent should help.
            """)

            ctx.data["report_agent"] = ConciergeAgent(
                name="Report Agent",
                parent=self,
                tools=[report],
                context=ctx,
                system_prompt=system_prompt,
                trigger_event=ReporterEvent
            )

        return ctx.data["report_agent"].handle_event(ev)


    @step(pass_context=True)
    async def fix_import(self, ctx: Context, ev: FixImportEvent) -> TextToDiagramEvent | ConciergeEvent:
        print(f"Syntax Check received request: {ev.request}")
        self.log_history(ctx, "fix_import", "user", ev.request)

        if "fix_import_agent" not in ctx.data:
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
                    organization_id="ORGANIZATION_ID",
                    api_key="API_KEY"
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

            system_prompt = f"""
            You are an advanced programming assistant specializing in checking and fixing the syntax of Python code. Follow these steps in order:
            ## 1. Initial Syntax Check
            - Use the `run_and_check_syntax` tool to execute temp_generated_code.py python file
            - If the code runs without errors, conclude that there are no syntax issues
            - If errors are encountered, proceed to step 2

            ## 2. Error Handling and Logging
            - If syntax errors are detected:
            - Use the `suggest_imports` tool to get the suggested imports for import errors.
            - Use the `fix_and_write_code` tool to rewrite new code and save.

            ## 3. Verification
            - After applying fixes, rerun the `run_and_check_syntax` tool to verify that all syntax issues have been resolved
            - If errors persist, repeat steps 2-3 as necessary
            - Once new code is written, ask the `text_to_diagram` tool to regenerate the drawing.
            
            Once you have completed fixing new code, you *must* call the tool named "done" to signal that you are done. Do this before you respond.
            If you don't know what to do call need_help.
            """

            ctx.data["fix_import_agent"] = ConciergeAgent(
                name="Fix Import Agent",
                parent=self,
                tools=[run_and_check_syntax, suggest_imports, write_to_file, fix_and_write_code],
                context=ctx,
                system_prompt=system_prompt,
                trigger_event=FixImportEvent
            )

        return ctx.data["fix_import_agent"].handle_event(ev)

    @step(pass_context=True)
    async def architecture_check(self, ctx: Context, ev: ArchitectureCheckEvent) -> ConciergeEvent:
        print(f"Architecture Check received request: {ev.request}")
        self.log_history(ctx, "architecture_check", "user", ev.request)

        if "architecture_check_agent" not in ctx.data:
            def check_architecture(architecture: str) -> str:
                """Useful for checking the architecture of the provided system."""
                print(f"Checking architecture for the provided system")
                # Here you would implement the actual architecture checking logic
                return "Architecture is valid"  # Placeholder response

            system_prompt = (f"""
                You are a helpful assistant that checks the architecture of systems.
                You can only check architecture for systems provided to you by the check_architecture tool, don't make them up. Trust the output of the check_architecture tool even if it doesn't make sense to you.
                Once you have checked the architecture, you *must* call the tool named "done" to signal that you are done. Do this before you respond.
                If the user asks to do anything other than check architecture, call the tool "need_help" to signal some other agent should help.
            """)

            ctx.data["architecture_check_agent"] = ConciergeAgent(
                name="Architecture Check Agent",
                parent=self,
                tools=[check_architecture],
                context=ctx,
                system_prompt=system_prompt,
                trigger_event=ArchitectureCheckEvent
            )

        return ctx.data["architecture_check_agent"].handle_event(ev)

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

