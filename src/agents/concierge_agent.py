from llama_index.core.workflow import Event, Context
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import FunctionCallingAgentWorker
from typing import List, Callable
from colorama import Fore, Style
import sys

sys.path.append("..")
from events.event_types import ConciergeEvent


class ConciergeAgent:
    def __init__(
        self,
        parent,
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

        def done() -> None:
            """When you complete your task, call this tool."""
            print(f"{self.name} is complete")
            self.context.data["redirecting"] = True
            parent.send_event(ConciergeEvent(just_completed=self.name))

        def need_help() -> None:
            """If the user asks to do something you don't know how to do, call this."""
            print(f"{self.name} needs help")
            self.context.data["redirecting"] = True
            parent.send_event(
                ConciergeEvent(request=self.current_event.request, need_help=True)
            )

        self.tools = [
            FunctionTool.from_defaults(fn=done),
            FunctionTool.from_defaults(fn=need_help),
        ]
        for t in tools:
            self.tools.append(FunctionTool.from_defaults(fn=t))

        agent_worker = FunctionCallingAgentWorker.from_tools(
            self.tools,
            llm=self.context.data["llm"],
            allow_parallel_tool_calls=False,
            system_prompt=self.system_prompt,
        )
        self.agent = agent_worker.as_agent()

    def handle_event(self, ev: Event):
        self.current_event = ev

        response = str(self.agent.chat(ev.request))
        print(Fore.MAGENTA + str(response) + Style.RESET_ALL)

        if self.context.data["redirecting"]:
            self.context.data["redirecting"] = False
            return None

        user_msg_str = input("> ").strip()
        return self.trigger_event(request=user_msg_str)
