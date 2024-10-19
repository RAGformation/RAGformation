from llama_index.core.workflow import step, Context, Workflow, Event
from llama_index.core.agent import FunctionCallingAgentWorker
from llama_index.llms.openai import OpenAI
import sys
sys.path.append("..")
from agents.concierge_agent import ConciergeAgent
from llama_index.core.tools import FunctionTool

from utils.llm_initializer import initialize_llm
from tools.diagram_tools import run_and_check_syntax, suggest_imports, fix_and_write_code, generate_diagram
from tools.rag_tools import search_rag
from events.event_types import (
    InitializeEvent, ConciergeEvent, OrchestratorEvent,
    TextToDiagramEvent, TextToRAGEvent,
)
from events.event_emitters import (
    emit_text_to_diagram,
    emit_concierge,
    emit_stop,
    emit_price_lookup,
    emit_text_to_rag,
    emit_report
)
from llama_index.core.workflow import (
    step,
    Context,
    Workflow,
    Event,
    StartEvent,
    StopEvent
)

sys.path.append("../..")
from dotenv import load_dotenv
load_dotenv()


search_rag("hwllo")