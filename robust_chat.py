#用来读取操作系统环境变量，你的 API 密钥就从环境变量读取。
import os
#提供`sleep()`休眠函数，**API 出错重试的时候用来等待一段时间**，限流、服务器报错时延迟再发起下一次请求。
import time

from dotenv import load_dotenv
from openai import OpenAI

'''APIConnectionError
网络层面错误：连不上服务器、断网、域名解析失败，请求根本没发到服务端。
APIStatusError
服务器返回 HTTP 错误状态码，比如 400 参数错、500 服务端崩溃。可以拿到e.status_code拿到 http 状态码。
AuthenticationError
鉴权失败:API_key 无效、密钥写错、密钥过期。
RateLimitError
触发接口限流 429,请求太频繁,配额用光'''
from openai import APIConnectionError,APIStatusError,AuthenticationError,RateLimitError

load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

def chat_with_retry(messages,max_retries=3):
    for attempt in range(1,max_retries+1):
        try:
            response=client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
            )
            return response.choices[0].message.content
        except AuthenticationError:
            print("错误:API KEY无效,请检查.env里的DEEPSEEK_API_KEY")
            return None
        except RateLimitError:
            print(f"限流(429),第{attempt}次后等待重试...")
            time.sleep(2*attempt)
        except APIStatusError as e:
            if 500<=e.status_code<600:
                print(f"服务器错误({e.status_code}):第{attempt}次后等待重试")
                time.sleep(2*attempt)
            else:
                print(f"API错误({e.status_code}):{e}")
                return None
        except APIConnectionError:
            print(f"网络连接失败,第{attempt}次后等待重试")
            time.sleep(29*attempt)
        except Exception as e:
            print(f"未知错误:{e}")
            return None
    print("重试3次后仍然失败")
    return None

answer=chat_with_retry([
    {"role":"user","content":"用一句话说明requests和openai库的区别"},
]
    
)
if answer:
    print("回答:",answer)
        