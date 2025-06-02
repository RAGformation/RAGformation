from llama_index.core.workflow import Event
from typing import Optional


class InitializeEvent(Event):
    pass


class ConciergeEvent(Event):
    request: Optional[str] = None
    just_completed: Optional[str] = None
    need_help: Optional[bool] = False


class OrchestratorEvent(Event):
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


class FixImportEvent(Event):
    request: str


class ArchitectureCheckEvent(Event):
    request: str
