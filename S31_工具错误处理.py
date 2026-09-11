#tool_error---重试 / 超时 / 失败回退

import os
import json
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# ---------- 工具 1：除法（可能业务报错） ---------
def divide(a:float,b:float)->float:
    if b==0:
        raise ValueError("除数不能为0")
    return a/b

# ---------- 工具 2：天气（可能查不到城市） ----------
def get_weather(city:str)->dict:
    data={
        "上海":"晴 26℃",
        "北京": "多云 22℃",
    }
    if city not in data:
        raise ValueError(f"没有找到城市{city}的天气数据")
    return {"city":city,"weather":data[city]}

# ---------- 工具 3：不稳定服务（模拟超时，第一次失败） ----------

flaky_state={"count":0}

def flaky_service()->str:
    flaky_state["count"]+=1
    if flaky_state["count"]<2:
        raise ValueError("模拟网络超时")
    return "服务已恢复正常"

#统计工具:(这一部分给程序看的)
TOOL_FUNCTIONS={
    "divide":divide,
    "get_weather":get_weather,
    "flaky_service":flaky_service
}

#介绍每一部分工具(给Agent看)
tools=[
    {
        "type":"function",
        "function":{
            "name":"divide",
            "description":"计算a除以b",
            "parameters":{
                "type":"object",
                "properties":{
                    "a":{"type":"number","description":"被除数"},
                    "b":{"type":"number","description":"除数"},
                },
                "required":["a","b"],
            },
        },
    },
    {
        "type":"function",
        "function":{
            "name":"get_weather",
            "description":"查询一个城市的天气",
            "parameters":{
                "type":"object",
                "properties":{
                    "city":{"type":"string","description":"城市名字 例如:上海"},
                },
                "required":["city"],
            },
        },
    },
    {
        "type":"function",
        "function":{
            "name":"flaky_service",
            "description":"调用一个不稳定的远程服务，可能会临时超时",
            "parameters":{
                "type":"object",
                "properties":{},
                "required":[],
            },
        },
    },
]

# 可以重试的错误类型（临时性问题）
TRANSIENT_ERRORS=(TimeoutError,ConnectionError)

#tool_ERROR函数
def execute_tool(name:str,args:dict,max_retries:int=2)->str:
    """执行工具，统一返回 JSON 字符串；出错不抛异常，而是把错误交回模型"""
    #1.name不对未知工具
    #2.为了出错不中断对话--(1.参数不对，2.TRANSIENT_ERRORS，3.业务错误，例如除以 0、城市不存在,4.未知异常)

    if name not in TOOL_FUNCTIONS:
        return json.dumps({"ok":False,"error":f"未知工具:{name}"},ensure_ascii=False)

    for attempt in range(1,max_retries+1):
        try:
            #获取工具调用结果
            result=TOOL_FUNCTIONS[name](**args)
            return json.dumps({"ok":True,"result":result},ensure_ascii=False)
        except TypeError as e:
            # 参数不对，重试也没意义
            return json.dumps({"ok":False,"error":f"参数错误: {e}"},ensure_ascii=False)
        except TRANSIENT_ERRORS as e:
            if attempt <=max_retries:
                print(f"临时错误{e},第{attempt}次尝试")
                time.sleep(1)
                continue
            else:
                return json.dumps({"ok":False,"error":f"重试{max_retries}次后仍能失败:{e}"},ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok":False,"error":f"工具执行失败：{e}"}, ensure_ascii=False)
    return json.dumps({"ok": False, "error": "未知异常"}, ensure_ascii=False)

def run_agent(user_input:str,max_retries:int=5):
    messages=[{"role":"user","content":user_input}]

    for step in range(1,max_retries):
        response=client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0,
            max_tokens=800
        )
        message=response.choices[0].message
        tool_calls=message.tool_calls
        print("模型内容: ",message.content)

        if not tool_calls:
            print("最终回答: ",message.content)
            return message.content

        messages.append(
            {
                "role":"assistant",
                "content":message.content or "",
                "tool_calls":[
                    {
                        "id":call.id,
                        "type":"function",
                        "function":{
                            "name":call.function.name,
                            "arguments":call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ],
            }
        )


        for call in tool_calls:
            name=call.function.name
            args=json.loads(call.function.arguments)
            print(f"决定调用工具:{name},参数:{args}")

            result_json=execute_tool(name,args)
            print("工具返回: ",result_json)


            messages.append(
                {
                    "role":"tool",
                    "tool_call_id":call.id,
                    "content":result_json
                }
            )
    print("达到最大轮数，仍未得到最终回答")
    return None


if __name__ == "__main__":
    run_agent("请计算 10 除以 0 的结果")