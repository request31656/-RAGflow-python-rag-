"""Streamlit session_state 工具：跨页面记住当前选中的知识库/文档/分页游标。

Streamlit 多页面间状态通过 st.session_state 共享。这里集中管理数据侧用到的几个 key，
并提供带默认值的 getter，避免页面里到处写 st.session_state.get(...)。
"""
from __future__ import annotations

import streamlit as st


def get(key: str, default=None):
    return st.session_state.get(key, default)


def set(key: str, value) -> None:
    st.session_state[key] = value


# 当前选中的知识库 id（文档页/切片页/检索页共用）
def current_dataset_id() -> str:
    return st.session_state.get("current_dataset_id", "")


def set_dataset_id(dataset_id: str) -> None:
    st.session_state["current_dataset_id"] = dataset_id


# 当前选中的文档 id（切片页用）
def current_document_id() -> str:
    return st.session_state.get("current_document_id", "")


def set_document_id(document_id: str) -> None:
    st.session_state["current_document_id"] = document_id


# 当前选中的对话助手 id（聊天页用）
def current_chat_id() -> str:
    return st.session_state.get("current_chat_id", "")


def set_chat_id(chat_id: str) -> None:
    st.session_state["current_chat_id"] = chat_id


# 当前选中的会话 id（聊天页用）
def current_session_id() -> str:
    return st.session_state.get("current_session_id", "")


def set_session_id(session_id: str) -> None:
    st.session_state["current_session_id"] = session_id


# 当前选中的记忆库 id（记忆页用）
def current_memory_id() -> str:
    return st.session_state.get("current_memory_id", "")


def set_memory_id(memory_id: str) -> None:
    st.session_state["current_memory_id"] = memory_id


def require_ragflow_key() -> bool:
    """没配 API key 时在页面顶部给提示。返回是否已配置。"""
    from .config import settings
    if not settings.ragflow_api_key:
        st.error("未配置 RAGFLOW_API_KEY。编辑 .env 填入后重启（ragflow web → 个人设置 → API key）。")
        return False
    return True
