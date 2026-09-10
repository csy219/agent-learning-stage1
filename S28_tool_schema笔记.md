### 理解 tools 的每个字段
字段	作用
type: "function"	表示这是一个函数工具
name	工具名，模型调用时用它
description	告诉模型这个工具干什么，写得越清楚，模型选得越准
parameters	参数结构，用 JSON Schema 描述
properties	每个参数的名字、类型、说明
required	哪些参数必填


为什么必须写 description：模型不会读你的 Python 代码，它只根据 description 判断该不该调用。工具描述写得差，模型就会乱调或漏调。

为什么 arguments 是字符串：模型返回的是 JSON 文本，要先用 json.loads 才能变成 Python 字典。