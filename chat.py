import os

from dotenv import load_dotenv
from openai import OpenAI

#1.读取.env里的DEEPSEEK_API_KEY
load_dotenv()

#2.创建DeepSeek 客户端
client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

#3.发送一次对话请求
response=client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role":"system","content":"你是python助教,回答不超过50个字,回答简洁"},
        {"role":"user","content":"用一句话解释什么是虚拟环境"}
    ],
   
    temperature=0.1,
    max_tokens=20,
)
print(response.choices[0].message.content)


