import asyncio
import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

SERVER_FILE=Path(__file__).with_name("S47_my_mcp_server.py")

SERVER_CONFIG={
    "my_tools":{
        "command":sys.executable,
        "args":[str(SERVER_FILE)],
        "transport":"stdio",
    }
}

async def main():
    client=MultiServerMCPClient(SERVER_CONFIG)
    tools=await client.get_tools()
    names=sorted(tool.name for tool in tools)
    print("从自己的MCP Server 拿到工具: ",names)


    by_name={tool.name: tool for tool in tools}

    if "add" in by_name:
        result=await by_name["add"].ainvoke({"a":12,"b":30})
        print("add(12,30)= ",result)

    if "get_current_time" in by_name:
        result=await by_name["get_current_time"].ainvoke({})
        print("当前时间: ",result)

    if "word_count"in by_name:
        result= await by_name["word_count"].ainvoke({"text":"你好 MCP"})
        print("字数=",result)


if __name__ =="__main__":
    asyncio.run(main())

