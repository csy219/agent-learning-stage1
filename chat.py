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
        {"role":"user","content":"用一句话解释什么是虚拟环境"}
    ],
)
print(response.choices[0].message.content)


