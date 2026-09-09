import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from fastapi import FastAPI,HTTPException,UploadFile
from fastapi.responses import StreamingResponse

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

class ChatRequest(BaseModel):
    message:str

app=FastAPI()

@app.post("/chat/stream")
async def ChatStream(req:ChatRequest):
    #新的函数类型:生成器函数
    def generate():
        stream=client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role":"system","content":"你是Python助教,回答简洁清楚"},
                      {"role":"user","content":req.message}
                      ],
            stream=True
        )
        for chunk in stream:
            delta=chunk.choices[0].delta.content
            if delta:
                #SSE流式输出格式:每条消息以data:开头,两个换行结束
                yield f"data:{delta}\n\n"

        #告诉客户端流式结束
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(),media_type="text/event-stream")