import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from fastapi import FastAPI,HTTPException,UploadFile,File,Form
from fastapi.responses import StreamingResponse

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

app=FastAPI()

ALLOWED_EXTENSIONS={".txt",".pdf"}
MAX_FILE_SIZE=2*1024*1024

class ChatRequest(BaseModel):
    message:str
    temperature:float=0.2

#普通接口判断是否正常
@app.get("/health")
def health():
    return {"status":"ok"}

#聊天接口
@app.post("/chat")
def chat(req:ChatRequest):
    return {
        "reply": f"收到你的消息: {req.message}",
        "temperature": req.temperature
    }

#上传文件接口
@app.post("/upload")
async def upload_file(file:UploadFile=File(...)):
    filename=file.filename or "unknown"
    ext=Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的类型文件:{ext},仅支持{ALLOWED_EXTENSIONS}"
        )

    content=await file.read()
    if len(content)>=MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="该文件超过2MB"
        )

    return {
        "filename":filename,
        "ext":ext,
        "File_Size":len(content)
    }

#输出流接口
@app.post("/ChatStream")
def ChatStream(req:ChatRequest):
    def generate():
        stream=client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role":"system","content":"你是Python助手,回答简洁清楚."},
                {"role":"user","content":req.message}
            ],
            stream=True
        )

        for chunk in stream:
            delta=chunk.choices[0].detal.content
            if delta:
                yield f"data:{delta}\n\n"

        yield "data:[DONE]\n\n"

    return StreamingResponse(generate(),media_type="text/event-stream")

#问答接口
@app.post("/ask")
async def ask(file:UploadFile=File(...),
              question:str=Form(...)):
    filename=file.filename or "unknown"
    ext=Path(filename).suffix.lower()

    if ext not in {".txt"}:
        raise HTTPException(
            status_code=400,
            detail=f"本接口目前只支持.txt文件(PDF解析后续步骤学习)"
        )

    content=await file.read()
    if len(content)>=MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="该文件超过了最大的2MB"
        )

    text=content.decode("utf-8",errors="ignore").strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="文件内容为空"
        )

    def generate():
        stream=client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role":"system",
                 "content":"你是文档问答助手。只能根据用户提供的文档内容回答；文档里没有答案时，直接说不知道，不要编造。"
                },
                {"role":"user",
                 "content":f"文档内容:\n{text}\n\n问题:{question}"
                }
            ],
            stream=True
        )

        for chunk in stream:
            delta=chunk.choices[0].delta.content
            if delta:
                yield f"data: {delta}\n\n"

        yield "data: [DONE]\n\n"
        
    return StreamingResponse(generate(),media_type="text/event-stream")