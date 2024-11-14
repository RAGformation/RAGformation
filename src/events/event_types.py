from llama_index.core.workflow import Event


class InitializeEvent(Event):
    pass


class ConciergeEvent(Event):
    request: str = ""
    just_completed: str = None
    need_help: bool = False


class OrchestratorEvent(Event):
    request: str


class TextToDiagramEvent(Event):
    request: str


class TextToRAGEvent(Event):
    request: str


class StopEvent(Event):
    pass


class StartEvent(Event):
    request: str


class PriceLookupEvent(Event):
    request: str


class ImageToTextEvent(Event):
    request: str


class ReporterEvent(Event):
    request: str


class FixImportEvent(Event):
    request: str


class ArchitectureCheckEvent(Event):
    request: str
