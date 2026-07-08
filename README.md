# My-RAG —— ragflow + Streamlit 精简 RAG 系统

以 [ragflow](https://github.com/infiniflow/ragflow) 为后端蓝本，去除复杂 React 前端、登录机制、模型商切换、智能体（可视化工作流），用 Streamlit 重写前端，无身份验证，只保留五大核心功能：**知识库、聊天、记忆、搜索、文件管理**。后端能力（解析/检索/存储/对话/记忆）全交给 ragflow docker。

## 架构

- `src/ragflow_api.py` —— ragflow HTTP API 薄封装（datasets/documents/chunks/files/retrieval/chats/sessions/completion/memories/messages/models）
- `src/agent.py` —— 流式问答编排（基于 ragflow chat assistant + session）
- `app.py` + `pages/` —— Streamlit 多页面前端
- `src/tracing.py` —— Langfuse @observe（空 key 降级）

## 快速开始

```bash
# 1. 装 Python 依赖
pip install -r requirements.txt

# 2. 起 ragflow（自带 ES/MySQL/MinIO/Redis 等全部依赖）
cd ragflow/docker
docker compose -p ragflow up -d
# 首次较慢（拉 ragflow 镜像 + DeepDoc 模型权重）

# 3. 配置
# 打开 http://localhost:9380 注册账号 → 个人设置建 API key
# 填到项目根 .env 的 RAGFLOW_API_KEY

# 4. 启动前端
streamlit run app.py
# 浏览器 http://localhost:8501
```

## 功能模块（左侧侧边栏导航）

| 页面 | 功能 |
|---|---|
| 📚 知识库 | 创建/列表/删除知识库，配置切片方法（naive/book/manual/qa/...） |
| 📁 文件管理 | user 文件空间，上传/删除/移入知识库 |
| 📄 文档 | 知识库内文档管理 + 上传 + 解析/停止/重解析 + 下载 + 状态轮询 |
| ✂️ 切片 | 分页查看 chunk + 编辑/新增/删除 + 关键词 |
| 🔎 检索测试 | 对知识库检索，看召回 chunks + 相似度 + 来源聚合 |
| 💬 聊天 | 对话助手(始终绑知识库) + 会话，流式 RAG 问答 + 引用片段 |
| 🧠 记忆 | 记忆库创建/列表/删除，消息查看/搜索/遗忘（独立于聊天） |

## 设计说明

- **无登录**：全程用单一 `RAGFLOW_API_KEY` 直连后端，不做身份验证。
- **不切模型商**：模型在 ragflow 后台配好，前端只选用，不暴露 provider 切换。
- **聊天始终绑知识库**：建对话助手时强制选知识库，走 RAG 问答（检索空时由服务端 LLM 兜底）。
- **记忆独立**：记忆库与聊天解耦，不在问答中自动读写记忆。
- **无智能体**：可视化工作流已去除（Streamlit 不适合画布）。

## 目录结构

```
RAG_project/
├── app.py                  # Streamlit 首页 + ragflow 连接检查
├── pages/                  # Streamlit 多页面（自动进侧边栏）
│   ├── 1_知识库.py
│   ├── 2_文件.py
│   ├── 3_文档.py
│   ├── 4_切片.py
│   ├── 5_检索测试.py
│   ├── 6_聊天.py
│   └── 7_记忆.py
├── src/
│   ├── ragflow_api.py      # ragflow HTTP 客户端
│   ├── agent.py            # 流式问答编排
│   ├── ui_state.py         # session_state 工具
│   ├── tracing.py          # Langfuse 装饰
│   ├── config.py           # 配置
│   └── evaluate.py         # 评测（占位）
├── .env                    # 配置
└── requirements.txt
```

## 进度

- [x] 架构转型：全调 ragflow HTTP，删自建 MySQL/Qdrant/MinIO
- [x] ragflow HTTP 客户端（datasets/documents/chunks/files/retrieval/chats/sessions/completion/memories/models）
- [x] Streamlit 多页面骨架 + 首页连接检查
- [x] 五大核心：知识库 / 文件管理 / 搜索 / 聊天(流式+引用) / 记忆(管理+搜索)
- [x] 流式问答（ragflow /chat/completions SSE）
- [~] Langfuse tracing（空 key 降级，已接入关键路径）
- [ ] RAGAS 评测（占位，非核心）
```
