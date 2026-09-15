import os
# ThreadPoolExecutor：让多个 Worker 并行执行；
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

#三个角色agent 的角色提示词
SUPERVISOR_PROMPT=(
    "你是任务主管。把用户的大任务拆成 2 到 4 个可独立完成的子任务。"
    "只输出 JSON,格式为 {\"subtasks\": [\"子任务1\", \"子任务2\"]}。"
)

WORKER_PROMPT=(
    "你是一个专注的执行者。只完成分配给你的这一个子任务，"
    "给出具体、可执行的结论，控制在 150 字以内。"
)

AGGREGATE_PROMPT=(
    "你是任务主管。把各个子任务的结果整合成一份最终方案，"
    "结构清晰，不要重复，不要编造子任务里没有的信息。"
)


class Plan(BaseModel):
    subtasks:list[str]


# 要是tokens不够用 就用这个加大tokens的用量
def call_llm(messages: list, max_tokens: int = 2000) -> str:
    """统一的模型调用：空内容自动加大额度重试一次"""
    for attempt in range(1, 3):
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            temperature=0,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        content = choice.message.content or ""

        print(
            f"[调用] 第{attempt}次 finish={choice.finish_reason} "
            f"completion_tokens={response.usage.completion_tokens} "
            f"content_len={len(content)}"
        )

        if content.strip():
            return content

        print("[警告] 返回内容为空，加大 max_tokens 重试")
        max_tokens *= 2

    return ""

#主管拆解任务
def plan_subtasks(task:str,max_subtasks:int=4)->list[str]:
    response=client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role":"system","content":SUPERVISOR_PROMPT},
            {"role":"user","content":task}
        ],
        response_format={"type":"json_object"},
        temperature=0,
        max_tokens=2000
    )
    content=response.choices[0].message.content or ""
    plan=Plan.model_validate_json(content)
    return plan.subtasks[:max_subtasks]

# worker执行子任务
def run_worker(subtask:str,index:int)->str:
    content=call_llm(
        [
            {"role": "system", "content": WORKER_PROMPT},
            {"role": "user", "content": f"子任务：{subtask}"},
        ]
    )
    return content or "(子任务未返回内容)"

#主管汇总
def aggregate(task:str,results:list[str])->str:
    joined="\n\n".join(
        f"子任务{i+1}的结果是: \n{result}"
        for i,result in enumerate(results)
    )

    content = call_llm(
        [
            {"role": "system", "content": AGGREGATE_PROMPT},
            {"role": "user", "content": f"总任务：{task}\n\n{joined}"},
        ],
        max_tokens=3000,
    )
    if content.strip():
        return content

    print("[警告] 汇总为空，退化为直接拼接子任务结果")
    return joined

def main():
    task = "我要给一个 LangGraph Agent 加入长期记忆，请给出可执行的实施方案。"
    subtasks=plan_subtasks(task,max_subtasks=3)

    print("主管拆解出的子任务: ")
    for i,subtask in enumerate(subtasks,1):
        print(f"{i}.{subtask}")

    # 三线程并发执行
    with ThreadPoolExecutor(max_workers=3) as executor:
        results=list(
            executor.map(run_worker,subtasks,range(1,len(subtasks)+1))
        )

    for i,result in enumerate(results,1):
        print(f"\n=======子Agent{i}的结果======")
        print(result)

    finally_result=aggregate(task,results)
    print("\n===== 主管汇总的最终方案 =====")
    print(finally_result)

if __name__=="__main__":
    main()