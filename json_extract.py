#S12 保证了模型输出是“合法 JSON”，但合法不等于正确

#  它是合法 JSON，但缺少 phone 和 date，程序直接取字段就会崩溃。S13 就是给模型输出加一道安检/质检：结构不对、缺字段、类型错误，第一时间报错，不让坏数据流进程序

import os
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

text="""张三的电话是 13812345678,他说 2026 年 10 月 1 日会到北京出差，
请帮他预订那天的酒店。"""

response=client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role":"system","content":("你是一个信息抽取助手。只输出 JSON,不要输出任何解释文字."
                                    "JSON 必须包含三个字段:name、phone、date。")},
        {"role":"user","content":f"请从下面文字中提取信息：{text}"}                            
    ],
    response_format={"type":"json_object"},
    temperature=0.1
)

content=response.choices[0].message.content
print(f"原先的输出:{content}")

data=json.loads(content)
print("解析后的字段: ")
print("姓名: ",data["name"])
print("电话: ",data["phone"])
print("日期: ",data["date"])

