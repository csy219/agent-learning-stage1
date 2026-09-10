import os
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

#工具
tools=[
    {
        "type":"function",
        "function":{
            "name":"add",
            "description":"计算两个数字的和，用于数学加法",
            "parameters":{
                "type":"object",
                "porperties":{
                    "a":{
                        "type":"number",
                        "description":"第一个数字"
                    },
                    "b":{
                        "type":"number",
                        "description":"第二个数字"
                    },
                },
                "required":["a","b"],
            },
        },
    },
]

messages=[
    {"role":"user","content":"请帮我计算 12 加 30 等于多少"}
]

response=client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    tools=tools,
    tool_choice="auto",
    temperature=0,
    max_tokens=800,
)

message=response.choices[0].message

print("模型文字回复: ",message.content)
print("结束原因: ",response.choices[0].finish_reason)


#看看模型有无选择工具
tool_calls=message.tool_calls

if tool_calls:
    for call in tool_calls:
        print("="*40)
        print("工具调用ID: ",call.id)
        print("工具调用名称: ",call.function.name)
        print("参数(json字符串): ",call.function.arguments)
        print("参数(Python 字典): ",json.loads(call.function.arguments))
else:
    print("模型没有调用工具,只做了文字回答")