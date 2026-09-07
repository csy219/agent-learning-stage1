1.system user assistant三者是什么：
system:给模型设定的：身份和行为规则
user:用户 （需要给模型提供问题）
assistant:助手：模型之前的回答 多轮对话必须把历史轮流放进去：user->assistant->user->assistant,模型才能记得上下文

2.一个带 system+user的请求JSON例子
{
    "model": "deepseek-chat",
    "messages":[
        {"role":"system","content": "你是python助教，回答要简短"}
        {"role":"user","content": "什么是 virtualenv?"}
    ]
}

3.用一句话说明“为什么多轮对话要保留 assistant 消息:
多轮对话必须把历史轮流放进去：user->assistant->user->assistant,模型才能记得上下文多轮对话必须把历史轮流放进去：