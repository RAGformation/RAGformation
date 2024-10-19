from llama_index.core.workflow import step, Context, Workflow, Event
from llama_index.core.agent import FunctionCallingAgentWorker
from llama_index.llms.openai import OpenAI
from agents.concierge_agent import ConciergeAgent
from llama_index.core.tools import FunctionTool

from utils.llm_initializer import initialize_llm
from tools.diagram_tools import run_and_check_syntax, suggest_imports, fix_and_write_code, generate_diagram
# from tools.rag_tools import search_rag
from raw_tool_fuctions.rag_tools import find_similar_blogs
from events.event_types import (
    InitializeEvent, ConciergeEvent, OrchestratorEvent,
    TextToDiagramEvent, TextToRAGEvent,
)
# from events.event_emitters import (
#     emit_text_to_diagram,
#     emit_concierge,
#     emit_stop,
#     emit_price_lookup,
#     emit_text_to_rag,
#     emit_report
# )
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
        ctx.data["history"].append({
            "at_step": agent,
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
            "history": [],
            "diagram_syntax_error": None,
            "diagram_node_arrangement_error": None,
            "requirements": None,
            "flow_confirmed": False,
            "rag_search_response": None,
            "query": "",
            "llm": initialize_llm("OpenAI"),
        })
        return ConciergeEvent()

    @step(pass_context=True)
    async def concierge(self, ctx: Context, ev: ConciergeEvent | StartEvent) -> InitializeEvent | StopEvent | OrchestratorEvent:
        if "user" not in ctx.data:
            return InitializeEvent()

        self.log_history(ctx, "concierge", "user", ev.request)
        print(f"History in concierge: {ctx.data['history']}")

        if "concierge" not in ctx.data:
            system_prompt = """
            You are a helpful assistant that is helping a user navigate an automatic architecture diagram assistant
            Your job is to ask the user questions to figure out what they want to do, and give them the available things they can do.
            That includes:
            * receiving the description of a system
            * draw a diagram from a description    
            * generate a report
            * exit
            You should start by listing the things you can help them do.            
            """

            ctx.data["concierge"] = FunctionCallingAgentWorker.from_tools(
                tools=[],
                llm=ctx.data["llm"],
                allow_parallel_tool_calls=False,
                system_prompt=system_prompt,
            ).as_agent()

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

        print(response)
        user_msg_str = input("> ").strip()
        ctx.data['query'] += f"\n\n{user_msg_str}"

        return OrchestratorEvent(request=user_msg_str)
        # return ctx.data["concierge"].handle_event(ev)

    @step(pass_context=True)
    async def orchestrator(self, ctx: Context, ev: OrchestratorEvent) -> ConciergeEvent | TextToDiagramEvent | TextToRAGEvent | StopEvent:
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

        tool_functions = [
            emit_concierge,
            emit_text_to_diagram,
            emit_stop,
            emit_text_to_rag,
        ]

        tools = [FunctionTool.from_defaults(fn=fn) for fn in tool_functions]

        system_prompt = """
        You are an advanced orchestrating agent designed to manage and optimize the execution of multiple subtasks within a complex workflow for AWS diagram generator, reporter and pricing. Your primary role is to coordinate between various tools, services, and APIs to ensure tasks are completed efficiently and accurately.
        Core responsibilities:
        - **Task delegation**: Assign each user request to the correct agent by calling the appropriate tool.
        - **Efficiency**: Ensure that you call only **one tool at a time**, allowing agents to handle their respective dependencies.
        - **Precision**: Match the user's request with the right agent without making redundant calls.
        - **Fail-safe**: If no tools are called, return the string "FAILED" without quotes and nothing else. This will signal that no matching agents were found for the request.
        - **No Dependency Resolution**: You do not need to handle or figure out dependencies between agents; each agent will manage its own dependencies and outputs.

        Behavioral Guidelines:
        - **Efficiency**: Make quick and accurate decisions about which agent to call based on the user's input. Avoid redundant calls or multiple agent invocations for a single task.
        - **Clarity**: Provide clear responses or actions based on the user's input.
        - **Accuracy**: Always select the most appropriate agent based on the request. If the request is ambiguous or cannot be understood, return "FAILED."
        - **No Overlap**: Each task should be handled by exactly one agent. If the task is outside your scope or the agents available, return "FAILED."
        
        Tools at your disposal:
        - **Text to Diagram Agent**: For converting text descriptions into a diagram.
        - **Text to RAG Agent**: For performing Retrieval-Augmented Generation (RAG) searches using to find similar usecases for the user query.
                        
        If you did not call any tools, return the string "FAILED" without quotes and nothing else.
        ### Decision Process:
        - Listen carefully to the user's request.
        - Based on the request, call the most suitable agent from the list above.
        - Do not attempt to resolve dependencies between agents; agents will handle their own logic.
        - If no suitable agent can be found for the user's request, respond with "FAILED."

        Ensure that your decisions are efficient and accurate to maintain a smooth workflow
        """

        if "orchestrator" not in ctx.data:
            ctx.data["orchestrator"] = FunctionCallingAgentWorker.from_tools(
                tools=tools,
                llm=ctx.data["llm"],
                allow_parallel_tool_calls=False,
                system_prompt=system_prompt,
            ).as_agent()

        response = str(ctx.data["orchestrator"].chat(ev.request))

        print(response)

        if response == "FAILED":
            print("Orchestration agent failed to return a valid speaker; try again")
            return OrchestratorEvent(request=ev.request)

    @step(pass_context=True)
    async def text_to_diagram(self, ctx: Context, ev: TextToDiagramEvent) -> OrchestratorEvent | ConciergeEvent:
        print(f"Text to Diagram received request: {ev.request}")
        print(f"real query for t2d: {ctx.data['rag_search_response']}")
        self.log_history(ctx, "text_to_diagram", "user", ev.request)
        
        if "text_to_diagram_agent" not in ctx.data:
            tools = [
                run_and_check_syntax,
                suggest_imports,
                fix_and_write_code,
                generate_diagram,
            ]

            system_prompt = """
                You are a specialized AWS assistant designed to generate architecture diagrams from provided text descriptions. Adhere to the following guidelines:
                - Use the `generate_diagram` tool to write code to generate a new diagram.
                - Use `run_and_check_syntax` tool to run the generated code to search for errors
                - If there are errors in running use the `fix_import` tool for fixing import errors.
                - Call the `fix_and_write_code` tool for other errors.
                - Apply the suggested changes
                - Use `run_and_check_syntax` tool to check if new diagram works.
                - Repeat the above steps till you have an error free diagram.
                
                - If no tools are called during the process, you you *must* call the tool named "done()" to signal that you are done OR
                - After successfully generating the diagram, you *must* call the tool named "done()" to signal that you are done.
                For all other requests or tasks, defer to other specialized agents using the `need_help` tool.
            """

            ctx.data["text_to_diagram_agent"] = ConciergeAgent(
                name="Text to Diagram Agent",
                parent=self,
                tools=tools,
                context=ctx,
                system_prompt=system_prompt,
                trigger_event=TextToDiagramEvent,
            )

        if not ctx.data["rag_search_response"]:
            print(ev)
            return TextToRAGEvent(request=ev.request)

        ctx.data['query'] += f"\n\n{ev.request}"

        return ctx.data["text_to_diagram_agent"].handle_event(ev)

    @step(pass_context=True)
    async def text_to_rag(self, ctx: Context, ev: TextToRAGEvent) -> TextToDiagramEvent | ConciergeEvent:
        print(f"Text to RAG received request: {ev.request}")
        self.log_history(ctx, "text_to_rag", "user", ev.request)
        
        def search_rag(text: str) -> str:
            """
            Perform a RAG (Retrieval-Augmented Generation) search using the provided text.
            """
            print(f"Performing a search from text: {text}")
            response = find_similar_blogs(text)
            print(response)
            ctx.data["rag_search_response"] = (
                f"### User query: \n {text}\n ### Results from RAG:\n {response}"
            )
            return response
        
        if "text_to_rag_agent" not in ctx.data:
            tools = [search_rag]

            system_prompt = """
                You are an efficient assistant specialized in conducting searches. 
                User will ask you some information or drawing an aws solution. you need to find a solution with similar usecase.
                Your role is to use the "search_rag" tool to retrieve relevant information based on the text provided. However, performing the search is optional—if the text already seems well-formed and sufficient, 
                you may simply respond with "This is very good, proceed with the architecture diagram."
                If the user requests any task unrelated to performing a search, use the "need_help" tool to signal that a different agent should handle the request.
                You are not permitted to generate information or search results on your own; you must rely solely on the output of the "search_rag" tool, even if it seems illogical.
            """

            ctx.data["text_to_rag_agent"] = ConciergeAgent(
                name="Text to RAG Agent",
                parent=self,
                tools=tools,
                context=ctx,
                system_prompt=system_prompt,
                trigger_event=TextToRAGEvent,
            )
        return ctx.data["text_to_rag_agent"].handle_event(ev)