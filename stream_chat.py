import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

response=client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role":"user","content":"请用 200字介绍 虚拟环境"}
    ],
    stream=True, #开启流式输出
    stream_options={"include_usage":True},
)

start=time.time()

for chunk in response:
    if chunk.usage is not None:
        print("\nusage:",chunk.usage)
    else:
        delta=chunk.choices[0].delta.content
        print(delta,end="", flush=True)

