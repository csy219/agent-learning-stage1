import os
import json
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


#工具 1
def add(a:float,b:float)->float:
    return a+b

#工具 2
def get_current_time()->str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#工具名字
TOOL_FUNCTIONS={
    "add":add,
    "get_current_time":get_current_time,
}

#工具说明书
tools=[
    {
        "type":"function",
        "function":{
            "name":"add",
            "description":"计算两个数字之和",
            "parameters":{
                "type":"object",
                "properties":{
                    "a":{"type":"number","description":"第一个数字"},
                    "b":{"type":"number","description":"第二个数字"},
                },
                "required":["a","b"],
            },
        },
    },
    {
        "type":"function",
        "function":{
            "name":"get_current_time",
            "description":"获取当前日期和时间",
            "parameters":{
                "type":"object",
                "properties":{},
                "required":[],
            },
        },
    },
]
def run_agent(user_input:str,max_retries=5):
    messages=[
        {"role":"user","content":user_input}
    ]
    for attempt in range(1,max_retries+1):
        response=client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0,
                max_tokens=800,
            )
        
        message=response.choices[0].message
        tool_calls=message.tool_calls
        print("模型内容: ",message.content)
        
        # 没有工具调用 → 模型给出了最终回答
        if not tool_calls:
            print("最终回答: ",message.content)
            return message.content
        
        # 把模型的“我要调用工具”这条消息加入历史
        assistant_message={
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
            ]
        }
        
        messages.append(assistant_message)
        
        
        # 逐个执行工具，并把结果回传给模型
        for call in tool_calls:
            name=call.function.name
            args=json.loads(call.function.arguments)
            print("决定调用工具: ",name,"参数: ",args)


            if name not in TOOL_FUNCTIONS:
                result=f"未知工具: {name}"
            else:
                try:
                    result=TOOL_FUNCTIONS[name](**args)
                except Exception as e:
                    result=f"工具执行失败: {e}"

            messages.append(
                {
                    "role":"tool",
                    "tool_call_id":call.id,
                    "content":json.dumps(result,ensure_ascii=False)
                }
            )

    print("达到最大轮数，仍未得到最终回答")
    return None


if __name__ == "__main__":
    run_agent("现在几点？另外帮我算 12 加 30 是多少")