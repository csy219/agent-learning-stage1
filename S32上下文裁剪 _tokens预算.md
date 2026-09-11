### 整体流程

用户输入问题
   ↓
messages.append(用户消息)
   ↓
ask() 先调用 trim_messages()
   ├─ 提取 system（永远保留）
   ├─ 从最新往旧累加
   └─ 超出预算就丢弃最旧的
   ↓
发送裁剪后的 messages 给模型
   ↓
拿到回答 + usage（真实 token）
   ↓
把 assistant 回答追加进 messages
   ↓
下一轮重复