"""聊天页面：选/建对话助手(始终绑知识库) → 选/建会话 → 流式问答 + 引用展示。"""
from __future__ import annotations

import streamlit as st

from src.agent import ask
from src.ragflow_api import (
    RagflowError,
    create_chat,
    create_session,
    delete_chats,
    delete_sessions,
    get_session,
    list_chats,
    list_datasets,
    list_sessions,
)
from src.ui_state import (
    current_chat_id,
    current_session_id,
    require_ragflow_key,
    set_chat_id,
    set_session_id,
)

st.set_page_config(page_title="聊天 - My-RAG", page_icon="💬", layout="wide")
st.title("💬 聊天")

if not require_ragflow_key():
    st.stop()


def _render_reference(ref):
    """渲染引用 chunks + 来源聚合。ref 可能是 {chunks, doc_aggs} 或 list[chunk]。"""
    chunks = []
    if isinstance(ref, dict):
        chunks = ref.get("chunks") or []
        doc_aggs = ref.get("doc_aggs") or []
        if doc_aggs:
            with st.expander("📎 来源文档", expanded=False):
                for agg in (doc_aggs if isinstance(doc_aggs, list) else []):
                    st.write(f"- {agg.get('doc_name', '')}：{agg.get('count', 0)} 条")
    elif isinstance(ref, list):
        chunks = ref
    if not chunks:
        return
    with st.expander(f"📎 引用片段（{len(chunks)}）", expanded=False):
        for i, c in enumerate(chunks, 1):
            if not isinstance(c, dict):
                continue
            content = c.get("content", c.get("content_with_weight", ""))
            doc = c.get("document_keyword", c.get("docnm_kwd", ""))
            sim = c.get("similarity", c.get("similarity_lt", 0))
            with st.expander(f"[{i}] {doc} · 相似度 {sim}"):
                st.write(content)


def _load_chats():
    try:
        data = list_chats(page=1, page_size=100)
        return data.get("chats") or data.get("data") or []
    except RagflowError as e:
        st.error(f"加载对话助手失败：{e}")
        return []


def _load_kbs():
    try:
        data = list_datasets(page=1, page_size=100)
        return data.get("kbs") or data.get("data") or []
    except RagflowError:
        return []


def _load_sessions(chat_id: str):
    try:
        return list_sessions(chat_id, page=1, page_size=100) or []
    except RagflowError as e:
        st.error(f"加载会话失败：{e}")
        return []


# ---- 选/建对话助手 ----
chats = _load_chats()
chat_options = {c["id"]: c.get("name", c["id"]) for c in chats if c.get("id")}

with st.expander("➕ 新建对话助手", expanded=not chat_options):
    kbs = _load_kbs()
    if not kbs:
        st.info("还没有知识库，先去「知识库」页建一个并解析文档。")
    else:
        kb_opts = {kb["id"]: kb.get("name", kb["id"]) for kb in kbs}
        with st.form("new_chat", clear_on_submit=True):
            name = st.text_input("名称 *")
            chosen_kbs = st.multiselect("绑定知识库 *（始终绑定，做 RAG 问答）",
                                        options=list(kb_opts.keys()),
                                        format_func=lambda k: kb_opts[k])
            desc = st.text_input("描述", value="A helpful Assistant")
            if st.form_submit_button("创建") and name.strip() and chosen_kbs:
                try:
                    res = create_chat(name=name, dataset_ids=chosen_kbs, description=desc)
                    if isinstance(res, dict) and res.get("id"):
                        set_chat_id(res["id"])
                    st.success(f"已创建「{name}」")
                    st.rerun()
                except RagflowError as e:
                    st.error(f"创建失败：{e}")

st.divider()

if not chat_options:
    st.info("还没有对话助手，点上方新建一个。")
    st.stop()

cur_chat = current_chat_id()
if cur_chat not in chat_options:
    cur_chat = list(chat_options.keys())[0]
sel_chat = st.selectbox("对话助手", options=list(chat_options.keys()),
                        index=list(chat_options.keys()).index(cur_chat),
                        format_func=lambda k: chat_options[k])
set_chat_id(sel_chat)

cc = st.columns([1, 1, 1])
if cc[0].button("🔄 刷新会话"):
    st.rerun()
if cc[1].button("🗑️ 删除此助手", type="primary"):
    try:
        delete_chats([sel_chat])
        set_chat_id("")
        set_session_id("")
        st.rerun()
    except RagflowError as e:
        st.error(f"删除失败：{e}")

st.divider()

# ---- 选/建会话 ----
sessions = _load_sessions(sel_chat)
session_options = {s["id"]: s.get("name", s["id"]) for s in sessions if s.get("id")}

sc = st.columns([3, 1])
cur_sess = current_session_id()
if cur_sess not in session_options:
    cur_sess = list(session_options.keys())[0] if session_options else ""
sel_sess = sc[0].selectbox("会话", options=list(session_options.keys()),
                           index=list(session_options.keys()).index(cur_sess) if cur_sess else 0,
                           format_func=lambda k: session_options[k]) if session_options else None
if sc[1].button("➕ 新建会话"):
    try:
        res = create_session(sel_chat, name=f"会话 {len(sessions) + 1}")
        if isinstance(res, dict) and res.get("id"):
            set_session_id(res["id"])
        st.rerun()
    except RagflowError as e:
        st.error(f"新建会话失败：{e}")

if sel_sess:
    set_session_id(sel_sess)
    mc = st.columns([1, 1])
    if mc[1].button("🗑️ 删除此会话", type="primary"):
        try:
            delete_sessions(sel_chat, [sel_sess])
            set_session_id("")
            st.rerun()
        except RagflowError as e:
            st.error(f"删除失败：{e}")

st.divider()

# ---- 对话区 ----
if not sel_sess:
    st.info("选一个会话或新建会话开始对话。")
    st.stop()

# 渲染历史
try:
    sess = get_session(sel_chat, sel_sess) or {}
except RagflowError as e:
    st.error(f"加载会话历史失败：{e}")
    sess = {}

messages = sess.get("messages", []) or []
references = sess.get("reference", []) or []
for i, m in enumerate(messages):
    role = m.get("role", "user")
    with st.chat_message(role if role in ("user", "assistant") else "assistant"):
        st.markdown(m.get("content", ""))
        # assistant 消息带引用（reference 列表按问答对顺序，索引需推算）
        if role == "assistant":
            ref_idx = (i - 1) // 2
            if isinstance(references, list) and 0 <= ref_idx < len(references):
                ref = references[ref_idx]
                _render_reference(ref)

# 新一轮问答
q = st.chat_input("输入问题…")
if q:
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        answer_box = st.empty()
        collected = ""
        last_ref: dict = {}
        try:
            with st.spinner("思考中…"):
                for delta, ref in ask(sel_chat, sel_sess, q):
                    collected += delta
                    if ref:
                        last_ref = ref
                    if collected:
                        answer_box.markdown(collected)
            if not collected:
                answer_box.info("（无回复）")
            if last_ref:
                _render_reference(last_ref)
        except RagflowError as e:
            answer_box.error(f"回答失败：{e}")
        st.rerun()
