import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

#反复问答函数
def ask(question:str,style:str)->str:
    if style=="plain":
        content=f"{question}\n请直接给出最终答案"
    else:
        content=f"{question}\n请先一步一步推理,再给出最终答案"

    response=client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role":"user","content":content}],
        temperature=0
    )
    return response.choices[0].message.content

questions = [
    "小明有 5 个苹果，给了小红 2 个，又买了 3 个，现在有几个苹果？",
    "如果 A 比 B 大 3 岁,B 比 C 大 2 岁,A 比 C 大几岁？",
    "3 个 5 相加，再加上 2 个 10,结果是多少？",
]

results=[]
#获取结果(元组)
for q in questions:
    plain=ask(q,"plain")
    cot=ask(q,"cot")
    results.append((q,plain,cot))

#拆开列表元组
for i,(q,plain,cot) in enumerate(results,1):
    print("="*50)
    print(f"问题{i}: {q}")
    print("\n直接回答: ")
    print(plain)
    print("\n一步一步思考: ")
    print(cot)
    