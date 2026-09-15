from datetime import datetime

from mcp.server.fastmcp import FastMCP

mcp=FastMCP("my_tools")

@mcp.tool()
def add(a:float,b:float)->float:
    """计算两个数字之和"""
    return a+b

@mcp.tool()
def get_current_time()->str:
    """获取当前的日期和时间"""
    return datetime.now().strftime("%Y-%m-%D %H:%M:%S")

@mcp.tool()
def word_count(test:str)->int:
    """统计一段文字的字数(按字符数)"""
    return len(test)

if __name__ == "__main__":
    mcp.run()
