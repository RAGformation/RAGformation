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
from llama_index.core.llms import ChatMessage
from llama_index.agent.openai import OpenAIAgent

from agent_scripts import text_to_diagram as draw_text_to_diagram
from events import InitializeEvent, ConciergeEvent, OrchestratorEvent, PriceLookupEvent, ImageToTextEvent, TextToDiagramEvent, TextToRAGEvent, ReporterEvent

import os

def load_env_file(file_path=".env"):
    try:
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    dotenv = None
    load_env_file()

from llama_index.core.workflow import (
    step,
    Context,
    Workflow,
    Event,
    StartEvent,
    StopEvent
)

class Message:
    role: str = None
    content: Optional[str] = None

# Centralize LLM initialization
def initialize_llm(llm_type: str):
    llm_map = {
        "AzureOpenAI": lambda: AzureOpenAI(engine="testing-first-gbu-doc", model="gpt-4o", temperature=0.4),
        "Ollama": lambda: Ollama(model="llama3.1:8b", request_timeout=120.0),
        "OpenAI": lambda:  OpenAI(model="gpt-4o",temperature=0.8),
        "Anthropic": lambda: Anthropic(model="claude-3-opus-20240229", temperature=0.4),
        "Groq": lambda: Groq(model="llama-3.1-70b-versatile", temperature=0.4),
    }
    return llm_map.get(llm_type, lambda: None)()

class ConciergeWorkflow(Workflow):

    @staticmethod
    def log_history(ctx: Context, agent, role, content):
        # TODO: log system prompts (on first call)
        # TODO: log assistant responses
        # TODO: convert to get/set format
        # TODO: log anything at all
        return
        # Version 0.10
        # ctx.data[set]agent].append({
        #     "role": role,
        #     "content": content,
        # })
        # Version 0.11
        # # Retrieve the data from ctx
        # data = ctx.get('data', {})
        #
        # # Get the list for the agent or initialize as an empty list if not present
        # agent_data = data.get(agent, [])
        #
        # # Append the new data
        # agent_data.append({
        #     "role": role,
        #     "content": content,
        # })
        #
        # # Put the updated list back into the data
        # data[agent] = agent_data
        #
        # # Set the updated data back into ctx
        # ctx.set('data', data)

    @step(pass_context=True)
    async def initialize(self, ctx: Context, ev: InitializeEvent) -> ConciergeEvent:
        ctx.data.update({
            "user": {"username": None, "session_token": None, "account_id": None},
            "success": None,
            "redirecting": None,
            "overall_request": None,
            "history": {agent: [] for agent in ["authenticate", "price_lookup", "image_to_text", "text_to_diagram", "text_to_rag", "report"]},
            "requirements": None,
            "flow_confirmed": False,
            "llm": initialize_llm("OpenAI")
            # "llm" : OpenAI(model="gpt-4o",temperature=0.8)
        })
        return ConciergeEvent()

    @step(pass_context=True)
    async def concierge(self, ctx: Context, ev: ConciergeEvent | StartEvent) -> InitializeEvent | StopEvent | OrchestratorEvent:
        # initialize user if not already done
        if "user" not in ctx.data:
            return InitializeEvent()

        # initialize concierge if not already done
        if "concierge" not in ctx.data:
            system_prompt = (f"""
                You are a helpful assistant that is helping a user navigate an automatic system AWS diagram generator, reporter and pricing.

                Behavioral Guidelines:
                - Be proactive: Suggest actions or steps that can improve efficiency or correctness.
                - Be transparent: Clearly explain each decision and the results of executed actions. If an action fails, explain why and attempt a fallback solution.
                - Be adaptive: Modify your behavior based on feedback from the environment or user instructions.
                - Be polite and helpful: Always maintain a helpful tone and seek the best possible outcomes for the user.
                - Be concise and clear: Use simple and concise language to avoid unnecessary details and confusion.
                Tools at Your Disposal:
                - price lookup
                - image to text
                - text to diagram
                - text to rag
                - reporter
                Your job is to ask the user questions to figure out what they want to do, and start by listing the things you can help them do:
                - Requirement gathering
                - Flow confirmation
                - Flow enhancement
                - Price lookup
                - Final report of selected flow 

                Then use the respective tool to fulfill the user's request.            
            """)
            ctx.data["concierge"] = FunctionCallingAgentWorker.from_tools(
                tools=[],  # <-- This is likely the cause of the error
                llm=ctx.data["llm"],
                allow_parallel_tool_calls=False,
                system_prompt=system_prompt
            ).as_agent()

        concierge = ctx.data["concierge"]
        if ctx.data["overall_request"]:
            last_request = ctx.data["overall_request"]
            ctx.data["overall_request"] = None
            return OrchestratorEvent(request=last_request)
        elif ev.just_completed:
            response = concierge.chat(f"FYI, the user has just completed the task: {ev.just_completed}")
        elif ev.need_help:
            print("The previous process needs help with ", ev.request)
            return OrchestratorEvent(request=ev.request)
        else:
            # first time experience
            response = concierge.chat("Hello!")

        print(Fore.MAGENTA + str(response) + Style.RESET_ALL)
        user_msg_str = input("> ").strip()
        return OrchestratorEvent(request=user_msg_str)

    @step(pass_context=True)
    async def orchestrator(self, ctx: Context, ev: OrchestratorEvent) -> ConciergeEvent | AuthenticateEvent | PriceLookupEvent | ImageToTextEvent | TextToDiagramEvent | TextToRAGEvent | ReporterEvent | StopEvent:
        print(f"Orchestrator received request: {ev.request}")

        # def create_emit_function(event_class):
        #     def emit():
        #         print(f"__emitted: {event_class.__name__.lower().replace('event', '')}")
        #         self.send_event(event_class(request=ev.request))
        #         return event_class(request=ev.request)
        #     return emit

        # tools = [
        #     FunctionTool.from_defaults(fn=create_emit_function(event_class))
        #     for event_class in [AuthenticateEvent, PriceLookupEvent, ImageToTextEvent, TextToDiagramEvent, TextToRAGEvent, ReporterEvent, ConciergeEvent, StopEvent]
        # ]

        print(f"Orchestrator received request: {ev.request}")

        def emit_stock_lookup() -> bool:
            """Call this if the user wants to look up a stock price."""
            print("__emitted: stock lookup")
            self.send_event(StockLookupEvent(request=ev.request))
            return True

        def emit_authenticate() -> bool:
            """Call this if the user wants to authenticate"""
            print("__emitted: authenticate")
            self.send_event(TextToDiagramEvent(request=ev.request))
            return True

        def emit_text_to_diagram() -> bool:
            """Call this if the user wants to authenticate"""
            print("__emitted: authenticate")
            self.send_event(TextToDiagramEvent(request=ev.request))
            return True

        def emit_account_balance() -> bool:
            """Call this if the user wants to check an account balance."""
            print("__emitted: account balance")
            self.send_event(AccountBalanceEvent(request=ev.request))
            return True

        def emit_transfer_money() -> bool:
            """Call this if the user wants to transfer money."""
            print("__emitted: transfer money")
            self.send_event(TransferMoneyEvent(request=ev.request))
            return True

        def emit_concierge() -> bool:
            """Call this if the user wants to do something else or you can't figure out what they want to do."""
            print("__emitted: concierge")
            self.send_event(ConciergeEvent(request=ev.request))
            return True

        def emit_stop() -> bool:
            """Call this if the user wants to stop or exit the system."""
            print("__emitted: stop")
            self.send_event(StopEvent())
            return True

        tools = [
            FunctionTool.from_defaults(fn=emit_stock_lookup),
            FunctionTool.from_defaults(fn=emit_authenticate),
            FunctionTool.from_defaults(fn=emit_account_balance),
            FunctionTool.from_defaults(fn=emit_transfer_money),
            FunctionTool.from_defaults(fn=emit_concierge),
            FunctionTool.from_defaults(fn=emit_text_to_diagram),
            FunctionTool.from_defaults(fn=emit_stop)
        ]

        system_prompt = (f"""
            You are an advanced orchestrating agent designed to manage and optimize the execution of multiple subtasks within a complex workflow for AWS diagram generator, reporter and pricing. Your primary role is to coordinate between various tools, services, and APIs to ensure tasks are completed efficiently and accurately.
            Core responsibilities:
            - **Task delegation**: Assign each user request to the correct agent by calling the appropriate tool.
            - **Efficiency**: Ensure that you call only **one tool at a time**, allowing agents to handle their respective dependencies.
            - **Precision**: Match the user’s request with the right agent without making redundant calls.
            - **Fail-safe**: If no tools are called, return the string "FAILED" without quotes and nothing else. This will signal that no matching agents were found for the request.
            - **No Dependency Resolution**: You do not need to handle or figure out dependencies between agents; each agent will manage its own dependencies and outputs.

            Behavioral Guidelines:
            - **Efficiency**: Make quick and accurate decisions about which agent to call based on the user's input. Avoid redundant calls or multiple agent invocations for a single task.
            - **Clarity**: Provide clear responses or actions based on the user’s input.
            - **Accuracy**: Always select the most appropriate agent based on the request. If the request is ambiguous or cannot be understood, return "FAILED."
            - **No Overlap**: Each task should be handled by exactly one agent. If the task is outside your scope or the agents available, return "FAILED."
            
            Tools at your disposal:
            - **Price Lookup Agent**: For checking the price of a service.
            - **Image to Text Agent**: For extracting text from an image.
            - **Text to Diagram Agent**: For converting text descriptions into a diagram.
            - **Text to RAG Agent**: For performing Retrieval-Augmented Generation (RAG) searches using text.
            - **Report Generation Agent**: For generating a report of the finalized flow.
            - **Concierge Agent**: For handling any other requests or questions not covered by the other agents.
                            
            If you did not call any tools, return the string "FAILED" without quotes and nothing else.
            ### Decision Process:
            - Listen carefully to the user's request.
            - Based on the request, call the most suitable agent from the list above.
            - Do not attempt to resolve dependencies between agents; agents will handle their own logic.
            - If no suitable agent can be found for the user's request, respond with "FAILED."

            Ensure that your decisions are efficient and accurate to maintain a smooth workflow. Your goal is to streamline task execution without unnecessary steps.
        """)

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
    async def authenticate(self, ctx: Context, ev: AuthenticateEvent) -> ConciergeEvent:

        self.log_history(ctx, "authenticate", "user", ev.request)

        if "authentication_agent" not in ctx.data:
            def store_username(username: str) -> None:
                """Adds the username to the user state."""
                print("Recording username")
                ctx.data["user"]["username"] = username

            def login(password: str) -> None:
                """Given a password, logs in and stores a session token in the user state."""
                print(f"Logging in {ctx.data['user']['username']}")
                # todo: actually check the password
                session_token = "output_of_login_function_goes_here"
                ctx.data["user"]["session_token"] = session_token

            def is_authenticated() -> bool:
                """Checks if the user has a session token."""
                print("Checking if authenticated")
                if ctx.data["user"]["session_token"] is not None:
                    return True

            system_prompt = (f"""
                You are a helpful assistant that is authenticating a user.
                Your task is to get a valid session token stored in the user state.
                To do this, the user must supply you with a username and a valid password. You can ask them to supply these.
                If the user supplies a username and password, call the tool "login" to log them in.
                Once you've called the login tool successfully, call the tool named "done" to signal that you are done. Do this before you respond.
                If the user asks to do anything other than authenticate, call the tool "need_help" to signal some other agent should help.
            """)

            ctx.data["authentication_agent"] = ConciergeAgent(
                name="Authentication Agent",
                parent=self,
                tools=[store_username, login, is_authenticated],
                context=ctx,
                system_prompt=system_prompt,
                trigger_event=AuthenticateEvent
            )

        return ctx.data["authentication_agent"].handle_event(ev)

    @step(pass_context=True)
    async def price_lookup(self, ctx: Context, ev: PriceLookupEvent) -> ConciergeEvent:

        print(f"Price Lookup received request: {ev.request}")
        self.log_history(ctx, "price_lookup", "user", ev.request)

        if "price_lookup_agent" not in ctx.data:
            def lookup_price(name: str) -> str:
                """Useful for looking the price of a service."""
                print(f"Looking up price for {name} service")

                # Call the pricingAgent.py to get the price of the service
                # get_price_for_service(name)

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
                The user can only request a price lookup if they have provided requirements, which you can check with the has_requirements tool.
                The user can only request a price lookup if they have confirmed the flow, which you can check with the has_requirement.
                The user may not know the name of the service they're interested in,
                so you can help them look it up by a description of what the service does or provides.
                You can only look up names given to you by the search_for_service tool, don't make them up. Trust the output of the search_for_service tool even if it doesn't make sense to you.
                Once you have retrieved a price, you must call the tool named "done" to signal that you are done. Do this before you respond.
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
                You are a helpful assistant that extracts text from image given as an input.
                Text extracted from the attached image is then sent to the text_to_rag tool for further processing.
                This function emits an event to trigger the text extraction process from the provided image.
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
    async def text_to_diagram(self, ctx: Context, ev: TextToDiagramEvent) -> ConciergeEvent:

        print(f"Text to Diagram received request: {ev.request}")
        self.log_history(ctx, "text_to_diagram", "user", ev.request)

        if "text_to_diagram_agent" not in ctx.data:
            def generate_diagram(text: str) -> str:
                """Useful for describing a diagram using text."""
                draw_text_to_diagram(text)

                return "Output diagram saved to output_diagram.png"

            system_prompt = (f"""
                You are a helpful assistant that generates a diagram from text.
                You can only generate diagrams from text given to you by the generate_diagram tool, don't make them up. Trust the output of the generate_diagram tool even if it doesn't make sense to you.
                Once you have generated the diagram, you *must* call the tool named "done" to signal that you are done. Do this before you respond.
                If the user asks to do anything other than generate a diagram, call the tool "need_help" to signal some other agent should help.
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

                response = call_rag_endpoint(text)

                return f"{response.get('result', 'No results found')} generated results"

            system_prompt = (f"""
                You are a helpful assistant that perform RAG searches from text.
                You can only search RAG from text given to you by the search_rag tool, don't make them up. Trust the output of the search_rag tool even if it doesn't make sense to you.
                Once you have performed the search, you *must* call the tool named "done" to signal that you are done. Do this before you respond.
                If the user asks to do anything other than perform a search, call the tool "need_help" to signal some other agent should help.
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