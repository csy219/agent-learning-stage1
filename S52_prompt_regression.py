# hashlib：给每个 Prompt 算指纹，防止“改了却没记录版本”
import os
import hashlib
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

MODEL="deepseek-v4-flash"
REPORT_FILE=Path("prompt_regression_report.json")

# 两个待比较的 Prompt 版本
PROMPT_VERSIONS={
    "v1":"你是 AI 助教，回答简洁准确，控制在三句话以内。",
    "v2":(
        "你是 AI 助教。回答要求："
        "1) 先给结论；"
        "2) 最多三句话；"
        "3) 涉及概念时给一个具体例子；"
        "4) 不确定就明确说不知道。"
    )
}

JUDGE_PROMPT = (
    "你是严格的评审员。根据参考答案判断回答是否正确。"
    "输出 JSON:{\"score\": 1-5, \"reason\": \"一句话理由\"}。"
    "评分标准："
    "5=完全正确，覆盖全部关键点，符合格式要求；"
    "4=正确但遗漏次要信息；"
    "3=部分正确，或关键点缺失；"
    "2=存在明显事实错误；"
    "1=编造信息、答非所问、内容为空，或泄露敏感信息。"
    "reason 必须指出具体缺失或错误。"
)

# 6 条精简回归集（成本控制；正式项目可用 S51 的完整 10+ 条）
GOLDEN_SET = [
    {"question": "什么是 Python 虚拟环境？", "must_contain": ["隔离"], "reference": "用于隔离不同项目的依赖。"},
    {"question": "temperature 设低有什么效果？", "must_contain": ["稳定"], "reference": "输出更稳定、更确定。"},
    {"question": "tool_call_id 的作用是什么？", "must_contain": ["对应"], "reference": "把工具结果和模型的调用申请配对。"},
    {"question": "什么是提示注入？", "must_contain": ["指令"], "reference": "诱导模型忽略原有指令的攻击方式。"},
    {"question": "LangGraph 的 Checkpointer 有什么用？", "must_contain": ["状态"], "reference": "保存图的状态，支持恢复与多轮记忆。"},
    {"question": "缓存能优化什么？", "must_contain": ["重复"], "reference": "相同请求直接返回，省钱省时间。"},
]

class JudgeResult(BaseModel):
    score:int
    reason:str

def answer_question(question:str,system_prompt:str):
    start=time.time()
    response=client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role":"system","content":system_prompt},
            {"role":"user","content":question}
        ],
        temperature=0,
        max_tokens=2000,
    )
    content=response.choices[0].message.content or ""
    usage=response.usage
    duration=round(time.time()-start,2)
    return content,usage.completion_tokens,duration

# 第 6 段：裁判结果模型与答题函数
def judge_answer(question:str,answer:str,reference:str)->JudgeResult:
    response=client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role":"system","content":JUDGE_PROMPT},
            {
                "role":"user",
                "content":(
                    f"问题: {question}\n"
                    f"参考答案: {reference}\n"
                    f"待评回答: {answer}"
                )
            }
        ],
        temperature=0,
        response_format={"type":"json_object"},
        max_tokens=2000
    )
    content=response.choices[0].message.content or ""
    return JudgeResult.model_validate_json(content)

# 第 8 段：评测函数与主流程
def evaluate(version:str,system_prompt:str)->dict:
    print(f"\n===== 评测 {version} =====")
    rows=[]

    for index,case in enumerate(GOLDEN_SET,1):
        answer,completion_tokens,duration = answer_question(case["question"],system_prompt)
        keyword_pass=all(keyword in answer for keyword in case["must_contain"])

        try:
            judged=judge_answer(case["question"],answer,case["reference"])
            score,reason=judged.score,judged.reason
        except Exception as e:
            score=0
            reason=f"评审失败: {e}"

        rows.append(
            {
                "index":index,
                "question":case["question"],
                "keyword_pass":keyword_pass,
                "score":score,
                "reason":reason,
                "duration":duration,
                "completion_tokens":completion_tokens
            }
        )
        print(
            f"{index} keyword={keyword_pass} score={score }"
            f"tokens={completion_tokens} time={duration}s"
        )
    total=len(rows)
    return {
        "version":version,
        # 整体作用：**对系统提示词 system_prompt 做哈希，取前 8 位十六进制字符串，作为 prompt 的简短指纹标识**，常用于日志、评测报告，快速区分不同 prompt 版本。
        "prompt_hash":hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:8],
        "keyword_pass_rate":round(sum(1 for r in rows if r["keyword_pass"])/total,3),
        "average_score":round(sum(r["score"] for r in rows)/total,2),
        "avg_completion_tokens":round(sum(r["completion_tokens"] for r in rows)/total,1),
        "avg_duration":round(sum(r["duration"] for r in rows)/total,2),
        "rows":rows,
    }


# 8.2 main：跑所有版本、选赢家
def main():
    results = [
    evaluate(version, prompt)
    for version, prompt in PROMPT_VERSIONS.items()
]
    # 排序规则：关键词通过率 > 平均分 > 更少的 token
    winner=max(
        results,
        key=lambda r:(
            r["keyword_pass_rate"],
            r["average_score"],
            -r["avg_completion_tokens"],
        ),
    )

    report={
        "model":MODEL,
        "versions":results,
        "winner":winner["version"],
    }
    REPORT_FILE.write_text(
        json.dumps(report,ensure_ascii=False,indent=0),
        encoding="utf-8"
    )
    print("\n=====版本对比=====")
    for r in results:
        print(
            f"{r['version']} (hash={r['prompt_hash']}) | "
            f"关键词通过率={r['keyword_pass_rate']:.0%} | "
            f"平均分={r['average_score']} | "
            f"平均输出 token={r['avg_completion_tokens']} | "
            f"平均耗时={r['avg_duration']}s"
        )
    print(f"\n推荐版本: {winner['version']}")
    print(f"报告已写入:{REPORT_FILE.resolve()} ")

if __name__ == "__main__":
    main()
