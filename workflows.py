from llama_index.core.workflow import (
    step,
    Context,
    Workflow,
    Event,
    StartEvent,
    StopEvent
)

LLM=None

try:
    from llama_index.llms.azure_openai import AzureOpenAI
    LLM = "AzureOpenAI"
except ImportError:
    try:
        from llama_index.llms.ollama import Ollama
        LLM = "Ollama"
    except ImportError:
        print("Unable to find a LLM")
from llama_index.core.agent import FunctionCallingAgentWorker
from llama_index.core.tools import FunctionTool
from llama_index.utils.workflow import draw_all_possible_flows
from typing import Optional, List, Callable
from colorama import Fore, Style

class InitializeEvent(Event):
    pass

class ConciergeEvent(Event):
    request: Optional[str] = None
    just_completed: Optional[str] = None
    need_help: Optional[bool] = False

class OrchestratorEvent(Event):
    request: str

class AuthenticateEvent(Event):
    request: str

class PriceLookupEvent(Event):
    request: str

class ImageToTextEvent(Event):
    request: str

class TextToDiagramEvent(Event):
    request: str

class TextToRAGEvent(Event):
    request: str

class ReporterEvent(Event):
    request: str

class ConciergeWorkflow(Workflow):

    @step(pass_context=True)
    async def initialize(self, ctx: Context, ev: InitializeEvent) -> ConciergeEvent:
        ctx.data["user"] = {
            "username": None,
            "session_token": None,
            "account_id": None,
        }
        ctx.data["success"] = None
        ctx.data["redirecting"] = None
        ctx.data["overall_request"] = None

        if LLM == "AzureOpenAI":
            ctx.data["llm"] = AzureOpenAI(
                engine="testing-first-gbu-doc", model="gpt-4o", temperature=0.4
            )
        elif LLM == "Ollama":
            ctx.data["llm"] = Ollama(model="llama3.1:8b", request_timeout=120.0)

        ctx.data["requirements"] = None
        ctx.data["flow_confirmed"] = False

        return ConciergeEvent()

    @step(pass_context=True)
    async def concierge(self, ctx: Context, ev: ConciergeEvent | StartEvent) -> InitializeEvent | StopEvent | OrchestratorEvent:
        # initialize user if not already done
        if "user" not in ctx.data:
            return InitializeEvent()

        # initialize concierge if not already done
        if "concierge" not in ctx.data:
            system_prompt = (f"""
                You are a helpful assistant that is helping a user navigate an automatic system diagram reporter.
                Your job is to ask the user questions to figure out what they want to do, and give them the available things they can do.
                That includes
                * authenticating the user
                * describe the requirements to the system for lookup
                * looking up the price of a service     
                * receiving the description of a system
                * draw a diagram from a description
                * generate a report
                You should start by listing the things you can help them do.            
            """)

            agent_worker = FunctionCallingAgentWorker.from_tools(
                tools=[],
                llm=ctx.data["llm"],
                allow_parallel_tool_calls=False,
                system_prompt=system_prompt
            )
            ctx.data["concierge"] = agent_worker.as_agent()

        concierge = ctx.data["concierge"]
        if ctx.data["overall_request"] is not None:
            print("There's an overall request in progress, it's ", ctx.data["overall_request"])
            last_request = ctx.data["overall_request"]
            ctx.data["overall_request"] = None
            return OrchestratorEvent(request=last_request)
        elif ev.just_completed is not None:
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

        def emit_authenticate() -> bool:
            """Call this if the user wants to authenticate"""
            print("__emitted: authenticate")
            self.send_event(AuthenticateEvent(request=ev.request))
            return True

        def emit_price_lookup() -> bool:
            """Call this if the user wants to look up the price of a service."""
            print("__emitted: price lookup")
            self.send_event(PriceLookupEvent(request=ev.request))
            return True

        def emit_image_to_text() -> bool:
            """Call this if the user wants to extract text from an image."""
            print("__emitted: image to text")
            self.send_event(ImageToTextEvent(request=ev.request))
            return True

        def emit_text_to_diagram() -> bool:
            """Call this if the user wants to describe a diagram using text."""
            print("__emitted: text to diagram")
            self.send_event(TextToDiagramEvent(request=ev.request))
            return True

        def emit_text_to_rag() -> bool:
            """Call this if the user wants to perform a RAG search using text."""
            print("__emitted: text to rag")
            self.send_event(TextToRAGEvent(request=ev.request))
            return True

        def emit_report() -> bool:
            """Call this if the user wants to generate a report."""
            print("__emitted: report")
            self.send_event(ReporterEvent(request=ev.request))
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
            FunctionTool.from_defaults(fn=emit_authenticate),
            FunctionTool.from_defaults(fn=emit_price_lookup),
            FunctionTool.from_defaults(fn=emit_image_to_text),
            FunctionTool.from_defaults(fn=emit_text_to_diagram),
            FunctionTool.from_defaults(fn=emit_text_to_rag),
            FunctionTool.from_defaults(fn=emit_report),
            FunctionTool.from_defaults(fn=emit_concierge),
            FunctionTool.from_defaults(fn=emit_stop)
        ]

        system_prompt = (f"""
            You are on orchestration agent.
            Your job is to decide which agent to run based on the current state of the user and what they've asked to do. 
            You run an agent by calling the appropriate tool for that agent.
            You do not need to call more than one tool.
            You do not need to figure out dependencies between agents; the agents will handle that themselves.
                            
            If you did not call any tools, return the string "FAILED" without quotes and nothing else.
        """)

        agent_worker = FunctionCallingAgentWorker.from_tools(
            tools=tools,
            llm=ctx.data["llm"],
            allow_parallel_tool_calls=False,
            system_prompt=system_prompt
        )
        ctx.data["orchestrator"] = agent_worker.as_agent()

        orchestrator = ctx.data["orchestrator"]
        response = str(orchestrator.chat(ev.request))

        if response == "FAILED":
            print("Orchestration agent failed to return a valid speaker; try again")
            return OrchestratorEvent(request=ev.request)

    @step(pass_context=True)
    async def authenticate(self, ctx: Context, ev: AuthenticateEvent) -> ConciergeEvent:

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

        if ("price_lookup_agent" not in ctx.data):
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
                The user can only request a price lookup if they have provided requirements and confirmed the flow, which you can check with the has_requirements tool and the flow_confirmed tool.
                You can only look up names given to you by the search_for_service tool, don't make them up. Trust the output of the search_for_service tool even if it doesn't make sense to you.
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

        if ("image_to_text_agent" not in ctx.data):
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
    async def text_to_diagram(self, ctx: Context, ev: TextToDiagramEvent) -> ConciergeEvent:

        print(f"Text to Diagram received request: {ev.request}")

        if ("text_to_diagram_agent" not in ctx.data):
            def generate_diagram(text: str) -> str:
                """Useful for describing a diagram using text."""
                print(f"Generating diagram from text {text}")
                return f"{text} generated a diagram"

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

        if ("text_to_rag_agent" not in ctx.data):
            def search_rag(text: str) -> str:
                """Useful for requesting a RAG search using text."""
                print(f"Performing a search from text {text}")
                return f"{text} generated results"

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

        if ("report_agent" not in ctx.data):
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

class ConciergeAgent():
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

draw_all_possible_flows(ConciergeWorkflow,filename="concierge_flows.html")

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
            asyncio.ensure_future(main())
    except RuntimeError:
        # For environments like Jupyter that may raise errors for nested event loops
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.run(main())
