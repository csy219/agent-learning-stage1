import os
from datetime import datetime
from typing import TypedDict,Annotated

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage,HumanMessage,SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START,END,StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode,tools_condition

load_dotenv()

llm=ChatOpenAI(
    model="deepseek-v4-flash",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0,
    max_tokens=800
)

@tool 
def add(a:float,b:float)->float:
    """两个数字相加,返回a与b的和"""
    return a+b

@tool
def get_current_time()->str:
    """获取当前系统时间，返回格式 YYYY-mm-dd HH:MM:SS"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 第 3 段：把工具绑定给模型
tools=[add,get_current_time]
llm_with_tools=llm.bind_tools(tools)

# 第 4 段：State 与消息累积规则（本文件关键）
class State(TypedDict):
    messages: Annotated[list[AnyMessage],add_messages]


# agent 节点
def agent_node(state:State)->dict:
    response=llm_with_tools.invoke(
        [
            SystemMessage(
                 content="你是助手。需要计算就调用 add,需要时间就调用 get_current_time。"
            ),
            *state["messages"],
        ]
    )
    return {"messages":[response]}

builder=StateGraph(State)
builder.add_node("agent",agent_node)
builder.add_node("tools",ToolNode(tools))

builder.add_edge(START,"agent")
builder.add_conditional_edges("agent",tools_condition)

builder.add_edge("tools","agent")

checkpointer=InMemorySaver()
graph=builder.compile(checkpointer=checkpointer)
print(graph.get_graph().draw_mermaid())


config={"configurable":{"thread_id":"demo_1"}}
questions=[
    "现在几点？",
    "12 加 30 等于多少？",
    "我刚才问了什么？",
]

for q in questions:
    print("\n===== 用户 =====")
    print(q)

    result=graph.invoke({"messages":[HumanMessage(content=q)]},config)
    print("===== 助手 =====")
    print(result["messages"][-1].content)


print("\n===== 内部消息流 =====")
for msg in result["messages"]:
    print("类型：", type(msg).__name__)
    print("内容：", msg.content)
    if getattr(msg, "tool_calls", None):
        print("工具调用：", msg.tool_calls)
    print("-" * 40)

