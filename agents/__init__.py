from agents.state import FaultLensState, initial_state
from agents.llm import get_chat_llm


def __getattr__(name: str):
    if name in ("build_graph", "get_graph"):
        from agents.graph import build_graph, get_graph

        return {"build_graph": build_graph, "get_graph": get_graph}[name]
    if name == "run_worker":
        from agents.worker import run_worker

        return run_worker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "build_graph",
    "get_graph",
    "FaultLensState",
    "initial_state",
    "run_worker",
    "get_chat_llm",
]
