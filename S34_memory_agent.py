import os
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

#2.四个全局配置

# SYSTEM_PROMPT：规定模型行为，改一处即可生效；
SYSTEM_PROMPT="你是学习助手，回答简洁，控制在三句话以内。"

# MEMORY_FILE：记忆持久化文件路径；
MEMORY_FILE=Path("memory_store.json")

# SUMMARY_TRIGGER：触发摘要的阈值，消息数超过它就压缩；
SUMMARY_TRIGGER=8

# KEEP_RECENT：压缩时保留最近几条，保证当前话题连贯。
KEEP_RECENT=4

#3.记忆库读写

# 返回的默认结构是“一段摘要 + 一个记忆列表”。
def load_store()->dict:
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"summary":"","memories":[]}

def save_store(store: dict):
    MEMORY_FILE.write_text(
        json.dumps(store,ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

#4. 检索记忆

#1.二元组(相似度计算)
def bigrams(text:str)->set:
    text=text.replace(" ","")
    return {text[i:i+2] for i in range(len(text)-1)}

#2.重合度打分
def retrieve_memories(query:str,memories:list,top_k:int=3)->list:
    query_pairs=bigrams(query)
    scored=[]

    for item in memories:
        score=len(query_pairs & bigrams(item["text"]))
        if(score>0):
            scored.append((score,item["text"]))

    scored.sort(key=lambda x:x[0],reverse=True)

# [text for _,text in scored[:top_k]的用法:

#     1. `for _, text in scored[:top_k]``scored[:top_k]` 里每一项是元组，比如 `(3, "面条很好吃")`
# 循环的时候自动**解包元组**：

# - 第一个值（分数）赋值给变量 `_`
# - 第二个值（文本）赋值给变量 `text`

# > 
# > `_` 是 Python 的约定：**这个变量我拿到了，但后面不会使用它**，用来占位。
# > 如果写成 `for score, text` 效果完全一样，只是我们不需要 score，就用下划线代替。

# 3. `text`（最前面那个）
# 每次循环，把 `text` 收集起来，组装成一个新列表。
    
    return[text for _,text in scored[:top_k]]

#5. 摘要记忆
def summarize(messages:list)->str:
    text="\n".join(f'{m["role"]}:{m["content"]}'for m in messages)

    response=client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {
                "role": "system",
                "content": "把下面的对话压缩成不超过 150 字的记忆摘要。"
                "必须保留：用户身份、学习目标、已做的决定、未完成的事。"
                "不要编造对话里没有的信息。",
            },
            {"role": "user", "content": text},
        ],
        temperature=0,
        max_tokens=800,
    )
    return response.choices[0].message.content or ""

#返回短时记忆 存入摘要
def maybe_compress(messages:list,store:dict)->list:
    if len(messages)<= SUMMARY_TRIGGER:
        return messages
    split_index=len(messages)-KEEP_RECENT
    old_messages=messages[:split_index]
    recent_messages=messages[split_index:]

    new_summary=summarize(old_messages)
    store["summary"]=(store["summary"]+"\n"+new_summary).strip()
    print("\n[记忆]已产生摘要: ",new_summary)
    return recent_messages

# 组装带记忆的上下文
def build_context(message:list,store:dict,question:str):
    context_parts=[]
    if store.get("summary"):
        context_parts.append("历史摘要: "+store["summary"])
    related=retrieve_memories(question,store.get("memories",[]))
    if related:
        context_parts.append("相关记忆: "+"\n"+"\n".join(related))

    result=[{"role":"system","content":SYSTEM_PROMPT}]
    if context_parts:
        result.append({"role":"system","content":"\n".join(context_parts)})
    result.extend(message)
    return result,related

def main():
    store=load_store()
    messages=[]

    questions = [
        "我叫小林，正在学 Agent,目标是找到 AI 应用开发的工作。",
        "我习惯先看官方文档，再自己动手写代码。",
        "帮我解释一下什么是向量数据库。",
        "我之前说过我的目标是什么？",
        "我之前说过我的学习习惯是什么？",
        "再帮我总结一下，我目前的方向和目标。",
    ]

    for i,question in enumerate(questions,1):
        print(f"------------第{i}轮-----------")
        messages.append({"role": "user", "content": question})

        context_messages, related = build_context(messages, store, question)
        print("检索到相关记忆：", related if related else "无")

        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=context_messages,
            temperature=0,
            max_tokens=800,
        )
        answer = response.choices[0].message.content or ""

        messages.append({"role": "assistant", "content": answer})

        # 把这一轮存进检索记忆
        store["memories"].append(
            {"text": f"用户：{question}\n助手:{answer}"}
        )

         # 太长就压缩成摘要
        messages = maybe_compress(messages, store)

        save_store(store)
        print("助手: ",answer)

if __name__=="__main__":
        main()