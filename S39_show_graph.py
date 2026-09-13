from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    text: str
    upper: str
    length: int


def make_upper(state: State) -> dict:
    return {"upper": state["text"].upper()}


def count_length(state: State) -> dict:
    return {"length": len(state["upper"])}


builder = StateGraph(State)
builder.add_node("make_upper", make_upper)
builder.add_node("count_length", count_length)
builder.add_edge(START, "make_upper")
builder.add_edge("make_upper", "count_length")
builder.add_edge("count_length", END)

graph = builder.compile()

print(graph.get_graph().draw_mermaid())