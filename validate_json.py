import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

#定义一个模板
class Contact(BaseModel):
    name:str
    phone:str
    date:str

#json转 模板函数
def extract_contact(text:str)->Contact:
    response=client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role":"system","content":"你是信息抽取助手。只输出 JSON,包含 name、phone、date 三个字段。"},
            {"role":"user","content":f"从下面文字提取联系人的信息: {text}"}
        ],
        response_format={"type":"json_object"},
        temperature=0
    )

    raw=response.choices[0].message.content
    print(f"模型返回: {raw}")

    try:
        contact=Contact.model_validate_json(raw)
        return contact
    except ValidationError as e:
        print(f"出错了: {e}")
        return None

if __name__=="__main__":
        text = "李四的电话是 13900001111,他计划 2026 年 11 月 15 日来上海。"
        contact=extract_contact(text)

        #print("校验成功")
        print("姓名: ",contact.name)
        print("电话: ",contact.phone)
        print("日期: ",contact.date)
        print("标准化json: ",contact.model_dump_json())