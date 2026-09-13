# TypedDict：声明 State 的键和类型；
# Literal：类型提示，表示“这个函数的返回值只能是 "math" 或 "chat" 这两个字符串之一”；
# END / START / StateGraph：搭图必备三件套。
from typing import Literal,TypedDict
from langgraph.graph import END,StateGraph,START


class State(TypedDict):
    question:str
    route:str
    answer:str

# classify 分类节点
def classify(state:State)->dict:
    question=state["question"]
    math_words=["计算", "加", "减", "乘", "除", "多少", "等于"]

    if any(word in question for word in math_words):
        route="math"
    else:
        route="chat"

    print("[classify]选择路由",route)
    return {"route":route}

# math分支节点
def math_node(state:State)->dict:
    print("[math_node] 执行数学分支")
    return {"answer":f"数学节点收到：{state['question']}"}

# chat 分支
def chat_node(state: State) -> dict:
    print("[chat_node] 执行聊天分支")
    return {"answer": f"聊天节点收到：{state['question']}"}

# 路由函数
def route_condition(state:State)->Literal["math","chat"]:
    return state["route"]

builder=StateGraph(State)
builder.add_node("classify",classify)
builder.add_node("math1",math_node)
builder.add_node("chat",chat_node)

builder.add_edge(START,"classify")

builder.add_conditional_edges(
    "classify",
    route_condition,
    {
        "math":"math1",
        "chat":"chat"
    }
)

builder.add_edge("math1",END)
builder.add_edge("chat",END)

graph=builder.compile()

# print(graph.get_graph().draw_mermaid())

for question in ["3 加 5 等于多少？", "你好，给我讲个笑话"]:
    print("\n===== 新问题 =====")
    result=graph.invoke({"question":question})
    print(result)


