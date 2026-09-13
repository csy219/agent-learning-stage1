import json
import os
import time

# ThreadPoolExecutor：实现“并行发请求”；
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

#2.CACHE_FILE：缓存存哪里；
CACHE_FILE=Path("cache.json")
SYSTEM_PROMPT="你是学习助手，回答简洁，控制在两句话以内。"


#3.缓存读写
def load_cache()->dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}

def save_cache(cache:dict)->None:
    CACHE_FILE.write_text(
        json.dumps(cache,ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

#4.ask —— 真正调用模型并记录指标
def ask(question:str,model:str)->dict:
    #start = time.time()：请求前记时间；
    start=time.time()
    response=client.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":question}
        ],
        temperature=0,
        max_tokens=800,
    )
    # elapsed：请求前后的时间差，即真实延迟
    elapsed=round(time.time()-start,2)
    # usage：API 返回的 token 统计，用来算成本。
    usage=response.usage


    # 能得到什么：一个“带性能指标”的调用封装，是优化的前提——不测量就没法优化
    return {
        "model":model,
        "answer":response.choices[0].message.content or "",
        "elapsed":elapsed,
        "prompt_tokens":usage.prompt_tokens,
        "completion_tokens":usage.completion_tokens
    }

# 5.cached_ask —— 缓存命中逻辑
def cached_ask(question:str,model:str)->dict:
    cache=load_cache()
    key=f"{model}|{question.strip()}"

    if key in cache:
        item=dict(cache[key])
        item["cached"]=True
        item["elapsed"]=0.0
        return item
    result=ask(question,model)
    result["cached"]=False
    cache[key]=result
    save_cache(cache)
    return result

# 6.choose_model —— 模型路由
def choose_model(question:str)->str:
    complex_words=["分析", "推理", "设计", "代码", "优化", "为什么", "对比"]
    if len(question) > 40 or any(word in question for word in complex_words):
        return "deepseek-v4-pro"
    return "deepseek-v4-flash"

# 7.demo_cache —— 验证缓存
def demo_cache():
    print("\n===== 实验 1:缓存 =====")
    question = "什么是虚拟环境？"

    first=cached_ask(question,"deepseek-v4-flash")
    print(f'第一次: cached={first["cached"]},耗时: {first["elapsed"]}')

    second = cached_ask(question, "deepseek-v4-flash")
    print(f"第二次:cached={second['cached']}, 耗时={second['elapsed']}s")


# 8.demo_parallel —— 串行 vs 并行
def demo_parallel():
    print("\n===== 实验 2:串行 vs 并行 =====")

    serial_questions = [
        "什么是 token?",
        "什么是 temperature?",
        "什么是上下文窗口?",
    ]

    parallel_questions = [
        "什么是向量数据库?",
        "什么是 embedding?",
        "什么是 RAG?",
    ]

    # 串行：一个接一个调用
    start = time.time()
    for q in serial_questions:
        ask(q, "deepseek-v4-flash")
    serial_time = round(time.time() - start, 2)

    # 并行：三个请求同时发，用不同的问题，避免命中缓存
    start = time.time()
    with ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(lambda q: ask(q, "deepseek-v4-flash"), parallel_questions))
    parallel_time = round(time.time() - start, 2)

    print(f"串行总耗时：{serial_time}s")
    print(f"并行总耗时：{parallel_time}s")
    print("说明：并行耗时接近最慢的一次请求，而不是三次相加。")

# 9.demo_routing 与程序入口
def demo_routing():
    questions = [
        "什么是 prompt?",
        "请分析为什么 RAG 会产生幻觉，并对比三种优化方案。",
    ]

    for q in questions:
        model=choose_model(q)
        result=cached_ask(q,model)
        print(f"问题：{q}")
        print(f"  选择模型：{model}")
        print(f"  tokens:prompt={result['prompt_tokens']}, completion={result['completion_tokens']}")
        print(f"  回答：{result['answer'][:60]}...")

if __name__ == "__main__":
    demo_cache()
    demo_parallel()
    demo_routing()