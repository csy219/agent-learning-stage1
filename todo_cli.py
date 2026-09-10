print("脚本开始运行")
import os
import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel,ValidationError

load_dotenv()

# 定义全局 Path 对象：待办保存文件 `todos.json`，后续读写都用这个
TODO_FILE=Path("todos.json")

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)
class Todo(BaseModel):
    action:str
    time:str
    object:str

def parse_todo(text:str,max_retries:int=3)->Todo:
    messages=[
        {"role":"system","content":"你是任务解析助手,把用户的话解析成json,必须包含 action time object三个字段, 只输出json"},
        {"role":"user","content":text}
    ]
    for attempt in range(1,max_retries+1):
        response=client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            response_format={"type":"json_object"},
            temperature=0,
            max_tokens=500
        )
        raw=response.choices[0].message.content
        print("模型原始输出：", repr(raw))
        print("结束原因：", response.choices[0].finish_reason)

        if not raw:
            print("模型返回了空内容，尝试重试...")
            continue

        try:
            return Todo.model_validate_json(raw)
        except ValidationError as e:
            print(f"第{attempt}次解析失败:{e.errors()}")
            messages.append({"role":"assistant","content":raw})
            messages.append({"role":"user","content":f"上面的输出不符合要求:{e.errors()},请修正后只输出json。"})
    raise RuntimeError("重试3次后仍然解析失败")



def save_todo(todo:Todo)->None:
    """把任务追加保存到 todos.json"""
    if TODO_FILE.exists():
        try:
            items=json.loads(TODO_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            items=[]
    else:
        items=[]

    items.append(todo.model_dump())
    TODO_FILE.write_text(
        json.dumps(items,ensure_ascii=False,indent=2),
        encoding="utf-8"
    )


def main():
        parser=argparse.ArgumentParser(description="自然语言转结构化待办")
        parser.add_argument("text",help="例如,明天上午10点提醒我交作业")
        args=parser.parse_args()

        try:
            todo=parse_todo(args.text)
        except RuntimeError as e:
            print("解析失败: ",e)
            return

        save_todo(todo)
        print("已解析: ",todo.model_dump())
        print("已保存到 todos.json")


if __name__== "__main__":
        main()