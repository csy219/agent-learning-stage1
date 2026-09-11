import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# 两个全局变量
SYSTEM_PROMPT="你是学习助手，回答尽量简短，控制在两句话以内。"
MAX_CONTEXT_TOKENS=150

# token估算器
def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    cjk=sum(1 for ch in text if "\u4e00" <= ch <="\u9fff")
    other=len(text)-cjk
    return (int)(cjk+other/4)+1

# 统计整个对话的token
def message_tokens(messages: list) -> int:
    total_tokens=0
    for m in messages:
        total_tokens+=estimate_tokens(m.get("content")or"")
    return total_tokens



# 裁剪上下文
def trim_context(messages: list,max_tokens:int=MAX_CONTEXT_TOKENS) ->list:
    """保留 system 消息 + 最近的对话，超出预算就丢掉最旧的"""
    system_msgs=[m for m in messages if m["role"]=="system"]
    others=[m for m in messages if m["role"]!="system"]
    # 选取一个空列表: 来装裁剪后的非system_msgs
    kept=[]
    #计算总tokens,先把固定的system的token装进去
    total_tokens=message_tokens(system_msgs)

    # 从最新往旧遍历，能放就放
    for m in reversed(others):
        cost_tokens=estimate_tokens(m.get("content")or "")
        if kept and (total_tokens+cost_tokens) > max_tokens:
            break
        kept.insert(0,m)
        total_tokens+=cost_tokens
    return system_msgs + kept


# 发送前裁剪+发送后核对
def ask(messages: list)->str:
    trimmed=trim_context(messages)

    print(
        f"原始消息数: {len(messages)},裁剪后: {len(trimmed)},"
        f"估算 token: {message_tokens(trimmed)}"
    )

    response=client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=trimmed,
        temperature=0,
        max_tokens=800,
    )
    #计算一下实际的tokens
    usage=response.usage
    print(
        f"实际prompt_tokens:{usage.prompt_tokens},completion_tokens: {usage.completion_tokens}")
    return response.choices[0].message.content


def main():
    messages=[{"role":"system","content":SYSTEM_PROMPT}]

    questions=[
        "我叫小林，正在学习 Python。",
        "我最喜欢的编程语言是 Python,因为语法简单。",
        "我最近在学 FastAPI 和 Agent。",
        "请用两句话介绍一下 FastAPI。",
        "根据前面的对话，我叫什么名字？我在学什么？",
    ]
    for i,question in enumerate(questions,1):
        print(f"\n--- 第 {i} 轮 ---")
        messages.append({"role": "user", "content": question})

        answer=ask(messages)
        messages.append({"role": "assistant", "content": answer})
        print("模型回答: ",answer)

if __name__ =="__main__":
    main()