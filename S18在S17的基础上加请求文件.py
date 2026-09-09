from pathlib import Path

from fastapi import FastAPI,File,HTTPException,UploadFile
from pydantic import BaseModel

app=FastAPI()

class ChatRequest(BaseModel):
    message:str
    temperature:float=0.2

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/chat")
def chat(req:ChatRequest):
    return {
        "reply":f"收到你的消息{req.message}",
        "temperature": req.temperature
    }


ALLOWED_EXTENSIONS={".txt","pdf"}
MAX_FILE_SIZE=2*1024*1024  #2MB

@app.post("/upload")
async def upload_file(file: UploadFile=File(...)):
    #1.取文件名和扩展名
    filename=file.filename or "unknown"
    ext=Path(filename).suffix.lower()

    #2.校验扩展名
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型:{ext},仅支持{ALLOWED_EXTENSIONS}类文件类型"
        )

    #3.读取1文件内容并且限制文件大小
    content=await file.read()
    if len(content)>=MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="文件超过2MB"
        )

    return{
        "filename":filename,
        "ext": ext,
        "size": len(content)
    }