"""My-RAG 首页：项目简介 + ragflow 连接状态检查。

数据侧多页面在 pages/ 目录下，Streamlit 自动在侧边栏生成导航。
"""
from __future__ import annotations

import streamlit as st

import src.tracing  # noqa: F401  Langfuse 装饰注册（空 key 降级）
from src.config import settings
from src.ragflow_api import RagflowError, list_datasets

st.set_page_config(page_title="My-RAG", page_icon="📚", layout="wide")

st.title("📚 My-RAG")
st.caption("以 ragflow 为后端、Streamlit 为前端的精简 RAG 系统。")

st.subheader("连接状态")
if not settings.ragflow_api_key:
    st.warning(
        "未配置 RAGFLOW_API_KEY。请：\n"
        "1. 启动 ragflow：`cd ragflow-main/ragflow-main/docker && docker compose -p ragflow up -d`\n"
        "2. 打开 http://localhost:9380 注册账号\n"
        "3. 个人设置里创建 API key，填到 `.env` 的 `RAGFLOW_API_KEY` 后重启"
    )
else:
    st.write(f"- ragflow 地址：`{settings.ragflow_base_url}`")
    st.write(f"- API key：`{settings.ragflow_api_key[:8]}...`")
    try:
        data = list_datasets(page=1, page_size=1)
        total = data.get("total", 0) if isinstance(data, dict) else len(data or [])
        st.success(f"✅ 已连接 ragflow，现有知识库 {total} 个")
        st.info("左侧侧边栏进入各功能页面。")
    except RagflowError as e:
        st.error(f"❌ 连接 ragflow 失败：{e}")
    except Exception as e:
        st.error(f"❌ 无法访问 ragflow（是否已 `docker compose up`？）：{e}")

st.divider()
with st.expander("功能模块（五大核心）"):
    st.markdown(
        "- 📚 **知识库**：创建/列表/删除知识库，配置切片方法；文档上传/解析、切片编辑\n"
        "- 💬 **聊天**：对话助手(始终绑知识库) + 会话，流式 RAG 问答，展示引用片段\n"
        "- 🧠 **记忆**：记忆库创建/列表/删除，消息查看/搜索/遗忘（独立于聊天）\n"
        "- 🔎 **搜索**：对知识库检索，看召回 chunks + 相似度 + 来源聚合\n"
        "- 📁 **文件管理**：user 文件空间，上传/删除/移入知识库\n"
    )
