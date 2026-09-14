import re
from datetime import datetime

from langchain_core.messages import AIMessage,HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END,START,StateGraph
from langgraph.prebuilt import ToolNode,tools_condition
from typing import Annotated,TypedDict
from langgraph.graph.message import add_messages

# 定义被测试的工具
@tool
def add(a:float,b:float)->float:
    """计算两个数字的和"""
    return a+b

@tool
def get_current_time():
    """获取当前日期和时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 测试 1，2
def test_add_tool():
    result=add.invoke({"a":12,"b":30})
    assert float(result)==42


# get_current_time.invoke({})：无参工具传空字典；
# 正则 \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} 匹配 2026-09-14 10:27:13；
# 不检查具体时间（会变），只检查格式，测试才稳定。
def test_get_current_time():
    result=get_current_time.invoke({})
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result)

# 构建工具调用信息
def make_ai_with_tool_call():
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name":"add",
                "args":{"a":12,"b":30},
                "id":"call_1",
                "type":"tool_call",
            }
        ],
    )

#测试3 路由-tools
def  test_tools_condition_routes_to_tools():
    state={"messages":[HumanMessage(content="算一下"),make_ai_with_tool_call()]}
    assert tools_condition(state)=="tools"

# 测试 4（无工具调用 → 结束）
def test_tools_condition_ends_without_tool_calls():
    state={"messages":[HumanMessage(content="你好"),AIMessage(content="你好呀")]}
    assert tools_condition(state)==END


# 测试 5（ToolNode 真正执行工具）

# 输入state messages: [ AIMessage(tool_calls: add(a=12,b=30)) ]
#         ↓
# ToolNode.invoke()
#         ↓
# 内部找到add工具 → add.invoke({"a":12,"b":30}) → 返回42
#         ↓
# 包装成 ToolMessage(content="42")，放到messages列表
#         ↓
# 输出新state，拿到ToolMessage，校验内容

class MessageState(TypedDict):
    messages: Annotated[list, add_messages]

def build_tool_graph():
    builder = StateGraph(MessageState)
    builder.add_node("tools", ToolNode([add]))
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    return builder.compile()

def test_tool_node_executes_add():
    graph = build_tool_graph()
    result = graph.invoke({"messages": [make_ai_with_tool_call()]})

    tool_message = result["messages"][-1]
    assert "42" in str(tool_message.content)

# 为记忆测试搭建小图
class CountState(TypedDict):
    turns:int

def increment_node(state:CountState)->dict:
    return {"turns":state.get("turns",0)+1}

def build_count_graph():
    builder=StateGraph(CountState)
    builder.add_node("increment",increment_node)
    builder.add_edge(START,"increment")
    builder.add_edge("increment", END)
    return builder.compile(checkpointer=InMemorySaver())

# 测试 6（记忆累加与会话隔离）
def test_checkpointer_accumulates_and_isolates():
    graph=build_count_graph()

    config_a={"configurable":{"thread_id":"test_a"}}
    config_b={"configurable":{"thread_id":"test_b"}}

    first=graph.invoke({},config_a)
    second = graph.invoke({}, config_a)
    other = graph.invoke({}, config_b)

    assert first["turns"] == 1
    assert second["turns"] == 2
    assert other["turns"] == 1



