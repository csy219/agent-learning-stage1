import os
import json
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# - TRACE_FILE 用 .jsonl 后缀：每行一条 JSON，追加方便、读起来也方便。
# 为什么用 JSONL 而不是一个 JSON 数组：
# - 追加时不用读整个文件、不用解析整个数组；
# - 写到一半崩溃也不会毁掉已有记录；
# - 生产日志系统（如 Kafka、ELK）都用这种格式。
# 能得到什么：一个只追加的本地 trace 存储。
TRACE_FILE=Path("traces.jsonl")

# 第 3 段：写 trace 的函数
def log_trace(record:dict)->None:
    with TRACE_FILE.open("a",encoding="utf-8") as f:
        f.write(json.dumps(record,ensure_ascii=False)+"\n")

# 第 4 段：核心封装 —— traced_llm 的入口
# 第 5 段：成功路径 —— 记录 trace
# 第 6 段：失败路径

def traced_llm(messages:list,step:str,run_id:str)->str:
    start=time.time()
    try:
        response=client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                temperature=0,
                max_tokens=2000,
            )
        content=response.choices[0].message.content
        usage=response.usage
        
        log_trace(
                {
                    "run_id":run_id,
                    "step":step,
                    "status":"ok",
                    "duration":round(time.time()-start,2),
                    "prompt_tokens":usage.prompt_tokens,
                    "completion_tokens":usage.completion_tokens,
                    "finish":response.choices[0].finish_reason,
                    "output_preview":content[:80]
                }
            )
        return content
    except Exception as e:
        log_trace(
            {
                "run_id":run_id,
                "step":step,
                "status":"error",
                "duration":round(time.time()-start,2),
                "error":str(e)
            }
        )
        raise

def main():
    run_id=str(uuid.uuid4())[:8]
    print("run_id",run_id)

    task = "用三句话说明为什么 Agent 需要可观测性。"

    step1 = traced_llm(
        [{"role": "user", "content": task}],
        "step1_ask",
        run_id,
    )
    step2 = traced_llm(
        [{"role": "user", "content": f"把下面内容压缩成两点：\n{step1}"}],
        "step2_compress",
        run_id,
    )
    step3 = traced_llm(
        [{"role": "user", "content": f"给出一个落地检查清单：\n{step2}"}],
        "step3_checklist",
        run_id,
    )

    print("\n最终结果:")
    print(step3)
    print("\ntrace 文件：", TRACE_FILE.resolve())


if __name__ == "__main__":
    main()