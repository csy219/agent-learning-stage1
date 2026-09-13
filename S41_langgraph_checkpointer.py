from typing import TypedDict

from langgraph.graph import END,START,StateGraph
from langgraph.checkpoint.memory import InMemorySaver

class State(TypedDict):
    question:str
    answer:str
    turns:int

def answer_turns(state:State)->dict:
    turns=state.get("turns",0)+1
    return {
        "answer":f"第{turns}次回答: {state['question']}",
        "turns":turns
    }

builder=StateGraph(State)
builder.add_node("answer_turns",answer_turns)
builder.add_edge(START,"answer_turns")
builder.add_edge("answer_turns",END)

# InMemorySaver()：创建一个检查点保存器；
# builder.compile(checkpointer=...)：- 告诉 LangGraph“每次执行节点后，把 State 存进这个检查点”；
# - 编译后返回的 graph 从此具备记忆能力。
checkpointer=InMemorySaver()
graph=builder.compile(checkpointer=checkpointer)


# 配置 thread_id
config_a={"configurable":{"thread_id":"user-a"}}
config_b={"configurable":{"thread_id":"user-b"}}

print("=== A 用户第一次 ===")
print(graph.invoke({"question":"你好，第一次"},config_a))

print("\n=== A 用户第二次（同一 thread_id)===")
print(graph.invoke({"question": "你好，第二次"}, config_a))
print("A的状态: ",graph.get_state(config_a).values)

print("\n=== B 用户（不同 thread_id)===")
print(graph.invoke({"question": "你好,B 用户"}, config_b))
print("B 的当前状态：", graph.get_state(config_b).values)
