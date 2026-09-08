from fastapi import FastAPI
from pydantic import BaseModel

#创建一个服务本体
app=FastAPI()

#限制收到的请求的格式
class ChatRequest(BaseModel):
    message:str
    temperature:float=0.2

#get装饰器
@app.get("/health")
def health():
    return {"status": "ok"}

#post 提交数据
@app.post("/chat")
def chat(req: ChatRequest):
    return {
        "reply":f"收到你的消息:{req.message}",
        "temperature": req.temperature
    }


