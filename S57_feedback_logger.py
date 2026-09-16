import json
import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 配置、演示知识库与系统提示
load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


# logs.jsonl：问答日志；
# feedback.jsonl：用户反馈；
# bad_cases.json：汇总的问题样本；
LOG_FILE=Path("logs.jsonl")
FEEDBACK_FILE=Path("feedback.jsonl")
BAD_CASE_FILE=Path("bad_cases.json")

KNOWLEDGE={
    "虚拟环境": "虚拟环境用于隔离不同项目的依赖，命令是 python -m venv .venv。",
    "token": "token 是模型处理文本的最小单位，也用于计费和上下文长度限制。",
    "Checkpointer": "Checkpointer 保存图的状态，用 thread_id 恢复多轮会话。",
}

SYSTEM_PROMPT = (
    "你是 AI 助教。只能根据提供的资料回答；"
    "资料里没有答案时，直接说不知道，不要编造。"
)

# JSONL 读写工具
# - "a"：追加模式，旧日志不丢；
# - ensure_ascii=False：中文正常保存；
# - 每条记录一行 → JSONL 格式。
# 为什么用追加而不是读改写：
# - 性能好：不用每次读整个文件；
# - 安全：程序中途崩溃不会毁掉已有日志；
# - 并发友好：多个请求可以先后追加。
def append_jsonl(path:Path,record:dict)->None:
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(record,ensure_ascii=False)+"\n")


# - 文件不存在返回空列表，避免首次运行报错；
# - splitlines() 按行切；
# - if line.strip() 跳过空行；
# - json.loads 把每行还原成字典。
# 能得到什么：一套通用的 JSONL 读写工具，日志、反馈、bad case 都能复用
def load_jsonl(path:Path)->list:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

# 检索函数
# - 遍历知识库的每个条目；
# - key in question：问题里出现关键词就算命中；
# - 命中后返回结构化的资料列表：source（来源标识）+ text（内容）。
# 为什么要带 source：回答时要能给出引用来源，这是 RAG 项目的基本要求（项目 A 会强化）。
# 为什么这只是演示版：关键词匹配无法处理同义表达，项目 A 会用 embedding + 向量检索替换它。
def retrieve(question:str)->list:
    """演示用检索: 命中关键词就返回资料"""
    results=[]
    for key,text in KNOWLEDGE.items():
        if key in question:
            results.append({"source":f"kb://{key}","text":text})
    return results


# 核心函数 —— ask_and_log
def ask_and_log(question:str)->tuple[str,str]:
    # 生成唯一 log_id：后续反馈靠它和日志关联；
    log_id=str(uuid.uuid4())[:8]
    sources=retrieve(question)

# 有资料：拼成带来源标记的上下文；
# 没资料：明确写“没有检索到资料”，让模型知道该怎么回答（说不知道）
    context=(
        "\n".join(f"[{s['source']}] {s['text']}" for s in sources)
        if sources
        else "没有检索到资料"
    )

    start=time.time()
    response=client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":'user',"content":f"资料:{context}\n 问题: {question}"}
        ],
        temperature=0,
        max_tokens=2000,
    )
    duration=round(time.time()-start,2)
    answer=response.choices[0].message.content or ""

    record={
        "log_id":log_id,
        "question":question,
        "answer_preview":answer[:150],
        "sources": ([s["source"] for s in sources]),
        "hit_knowledge":bool(sources),
        "duration":duration,
        "prompt_tokens":response.usage.prompt_tokens,
        "completion_tokens":response.usage.completion_tokens
    }
    append_jsonl(LOG_FILE,record)

    return log_id,answer

# 用户反馈记录
def mark_feedback(log_id:str,feedback:str,note:str="")->None:
    """feedback 取值 useful/useless/wrong"""
    append_jsonl(
        FEEDBACK_FILE,
        {
            "log_id":log_id,
            "feedback":feedback,
            "note":note,
            "ts":time.time()
        }
    )
# 导出 bad case
def export_bad_cases()->list:
    logs={r["log_id"]:r for r in load_jsonl(LOG_FILE)}
    feedback={r["log_id"]:r for r in load_jsonl(FEEDBACK_FILE)}


# 判定为 bad case 的三个条件：
# 1. 用户明确说没用/答错；
# 2. 没命中知识库；
# 3. 没有任何引用来源。
    bad_cases=[]
    for log_id,record in logs.items():
        fb=feedback.get(log_id,{})
        is_bad=(
            fb.get("feedback") in ("useless","wrong")
            or not record.get("hit_knowledge")
            or not record.get("sources")
        )

        if is_bad:
            bad_cases.append(
                {
                    **record,
                    "feedback":fb.get("feedback","无"),
                    "feedback_note":fb.get("note",""),
                }
            )
    BAD_CASE_FILE.write_text(
        json.dumps(bad_cases,ensure_ascii=False,indent=2),
        encoding="utf-8"
    )
    return bad_cases


def main():
    questions = [
        "什么是 Python 虚拟环境？",
        "Checkpointer 有什么用？",
        "LangGraph 的 memory_saver 参数默认值是多少？",
    ]
    log_ids=[]
    for question in questions:
        log_id,answer=ask_and_log(question)
        log_ids.append(log_id)
        print(f"\n[{log_id}] 问题: {question}")
        print(f"回答: {answer[:120]}")

    # 模拟用户反馈：第三条标为 wrong
    mark_feedback(log_ids[2],"wrong","编造了不存在的参数")

    bad_cases=export_bad_cases()
    print(f"\n日志已写入:{LOG_FILE.resolve()}")
    print(f"反馈已写入：{FEEDBACK_FILE.resolve()}")
    print(f"Bad case 数量：{len(bad_cases)}")
    print(f"Bad case 文件：{BAD_CASE_FILE.resolve()}")


    for case in bad_cases:
        print(f"- [{case['log_id']}] {case['question']} | 命中知识库={case['hit_knowledge']} | 反馈 {case['feedback']}")

if __name__ == "__main__":
    main()





