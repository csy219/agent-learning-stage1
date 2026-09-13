import os

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv()


llm=ChatOpenAI(
    model="deepseek-v4-flash",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0
)

prompt=ChatPromptTemplate.from_messages(
    [
        ("system","你是 Python 助教，回答简洁，控制在两句话以内。"),
        ("user","{question}")
    ]
)

chain=prompt | llm | StrOutputParser()

answer=chain.invoke({"question":"用一句话解释什么是 Chain"})
print(answer)