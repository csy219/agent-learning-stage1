import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel,ValidationError

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

class Contact(BaseModel):
    name:str
    phone:str
    date:str

def extract_with_retry(text:str,max_retries:int=3)->Contact:
    messages=[
        {"role":"system","content":"你是信息抽取助手。只输出 JSON,必须包含 name、phone、date 三个字段。"},
        {"role":"user","content":f"从下文提起联系人的信息: {text}"},
    ]
    for attempt in range(1,max_retries+1):
        print(f"----第{attempt}次尝试----")

        response=client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            response_format={"type":"json_object"},
            temperature=0
        )

        raw=response.choices[0].message.content
        # raw = '{"name": "赵六"}'
        print("模型输出: ",raw)

        try:
            contact=Contact.model_validate_json(raw)
            print("校验通过!")
            return contact
        except ValidationError as e:
            error_info=e.errors()
            print("校验失败,错误信息: ",error_info)

            #错误回传给上一轮对话的AI
            messages.append({"role":"assistant","content":raw})
            #让他修正
            messages.append({"role":"user","content":f"你刚才输出不符合要求: {error_info}。请修正后只输出正确的json"})
    raise RuntimeError(f"重试{attempt}次后仍然失败")
if __name__=="__main__":
    text = "赵六的电话是 13712345678,他 2027 年 1 月 20 日开会。"

    contact=extract_with_retry(text)

    print("最终结果: ",contact.model_dump())