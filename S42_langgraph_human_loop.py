# TypedDict：声明 State 的字段和类型；
# InMemorySaver：检查点保存器，中断暂停时必须用它存状态；
# END / START / StateGraph：搭图三件套；
# interrupt：在节点里调用它，图就会暂停；
# Command：恢复执行时用它把人工决定送回去。

from typing import TypedDict

from langgraph.graph import START,END,StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command,interrupt


# request：用户原始请求；
# action：Agent 打算执行的动作（危险操作描述）；
# approved：人工是否批准；
# result：最终执行结果。

class State(TypedDict):
    request:str
    action:str
    approved:bool
    result:str

# 计划节点plan_node
def plan_node(state:State)->dict:
    print("[plan_node] 生成待执行动作")
    return {"action":f"危险操作:{state['request']}"}

# 确认节点
def confirm_node(state:State)->dict:
    print("[confirm_node] 暂停，等待人工确认")

    decision=interrupt(
        {
            "question":f"是否批准执行:{state['action']}",
            "options":["批准","拒绝"]
        }
    )

    print("[confirm_node]收到人工请求",decision)
    return {"approved":bool(decision)}

# 执行
def execute_node(state:State)->dict:
    if(state.get("approved")):
        print("[execute_node] 已批准，执行动作")
        return {"result":f"已执行: {state['action']}"}

    print("[execute_node] 未批准,取消动作")
    return {"result":f"未执行: {state['action']}"}


#graph
builder=StateGraph(State)
builder.add_node("plan_node",plan_node)
builder.add_node("confirm_node",confirm_node)
builder.add_node("execute_node",execute_node)

builder.add_edge(START,"plan_node")
builder.add_edge("plan_node","confirm_node")
builder.add_edge("confirm_node","execute_node")
builder.add_edge("execute_node",END)

#存记忆 创建对象
checkpointer=InMemorySaver()
graph=builder.compile(checkpointer=checkpointer)


#记忆点
config_approve={"configurable":{"thread_id":"demo_approve"}}

print("\n===== 场景 1:发起操作 =====")
first=graph.invoke({"request":"删除过期日志"},config_approve)
print("第一次返回值: ",first)
print("当前中断信息: ",graph.get_state(config_approve).tasks)

print("\n===== 场景 1:人工批准 =====")
second=graph.invoke(Command(resume=True),config_approve)
print("批准后答案: ",second)


config_reject={"configurable":{"thread_id":"demo_reject"}}

third=graph.invoke({"request":"清空数据库"},config_reject)
print("第一次返回值",third)

fourth=graph.invoke(Command(resume=False),config_reject)
print("拒绝后结果: ",fourth)





    


