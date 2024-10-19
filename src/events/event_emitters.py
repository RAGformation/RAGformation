import sys
sys.path.append("..")
from events.event_types import (
    TextToDiagramEvent,
    ConciergeEvent,
    StopEvent,
    PriceLookupEvent,
    TextToRAGEvent,
    ReporterEvent
)

def emit_text_to_diagram(*args, **kwargs) -> bool:
    """Call this if the user wants to text to diagram"""
    ctx = kwargs.get('ctx')
    print("__emitted: text to diagram")
    ctx.send_event(TextToDiagramEvent(request=ev.request))
    return True

def emit_concierge(*args, **kwargs) -> bool:
    """Call this if the user wishes to perform another action, or if you’re unsure of their intent. You can also call this to prompt a response from the user.​"""
    ctx = kwargs.get('ctx')
    print("__emitted: concierge")
    ctx.send_event(ConciergeEvent(request=ev.request))
    return True

def emit_stop(*args, **kwargs) -> bool:
    """Call this if the user wants to stop or exit the system."""
    ctx = kwargs.get('ctx')
    print("__emitted: stop")
    ctx.send_event(StopEvent())
    return True

def emit_price_lookup(*args, **kwargs) -> bool:
    """Call this if the user wants to look up a price"""
    ctx = kwargs.get('ctx')
    print("__emitted: price lookup")
    ctx.send_event(PriceLookupEvent(request=ev.request))
    return True

def emit_text_to_rag(*args, **kwargs) -> bool:
    """Call this if the user wants to perform a text to RAG search"""
    ctx = kwargs.get('ctx')
    print("__emitted: text to rag")
    ctx.send_event(TextToRAGEvent(request=ev.request))
    return True

def emit_report(*args, **kwargs) -> bool:
    """Call this if the user wants to generate a report"""
    ctx = kwargs.get('ctx')
    print("__emitted: report")
    ctx.send_event(ReporterEvent(request=ev.request))
    return True