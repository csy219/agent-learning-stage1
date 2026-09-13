from typing import TypedDict
from langgraph.graph import END,START,StateGraph

class State(TypedDict):
    # 原始文本
    text:str
    # 大写结果
    upper:str
    # 长度
    length:int

# 节点1
def make_upper(state:State)->dict:
    print("[节点] make_upper 执行")
    return {"upper":state["text"].upper()}

# 节点2
def count_length(state:State)->dict:
    print("[节点] count_length 执行")
    return {"length":len(state["upper"])}

# 节点3
def reverse_text(state:State)->dict:
    print("[节点] reverse_text")
    return {"upper":state["text"][::-1]}

builder=StateGraph(State)

builder.add_node("make_upper",make_upper)
builder.add_node("count_length",count_length)
builder.add_node("reverse_text",reverse_text)

builder.add_edge(START,"make_upper")
builder.add_edge("make_upper","count_length")
builder.add_edge("count_length", "reverse_text")
builder.add_edge("reverse_text", END)

graph=builder.compile()

graph.get_graph().print_ascii

result=graph.invoke({"text":"hello langgraph"})
print(result)
