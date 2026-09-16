import os

from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

app=FastAPI()

class ChatRequest(BaseModel):
    message:str

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/chat/streaming")
def get(req:ChatRequest):
    def generate():
        stream=client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role":"system","content":"你是助手，回答简洁清楚。"},
                {'role':"user","content":req.message}
            ],
            stream=True
        )

        for chunk in stream:
            delta=chunk.choices[0].delta.content
            if delta:
                yield f"data:{delta}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(generate(),media_type="text/event-stream")
