from typing import TypedDict
from langgraph.graph import END,START,StateGraph

class State(TypedDict):
    question:str
    answer:str

#定义节点函数
def answer_node(state:State)->dict:
    return {"answer":f"我收到可你的问题: {state['question']}"}


# StateGraph(State)：创建一个图，并告诉它“这个图用 State 作为共享数据”；返回的 builder 是构建器，用来加节点、加边；
builder=StateGraph(State)

builder.add_node("answer_node",answer_node)
builder.add_edge(START,"answer_node")
builder.add_edge("answer_node",END)

# 把节点和边编译成一个可执行对象；
graph=builder.compile()

result=graph.invoke({"question":"什么是 State?"})
print(result)

