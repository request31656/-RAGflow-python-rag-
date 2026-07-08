"""记忆页面：创建/列表/删除记忆库，进入后查看消息、搜索、遗忘。

记忆与聊天解耦：不在聊天中自动读写记忆，此页独立管理。
"""
from __future__ import annotations

import streamlit as st

from src.ragflow_api import (
    MEMORY_TYPES,
    RagflowError,
    create_memory,
    delete_memory,
    forget_message,
    list_added_models,
    list_memories,
    list_memory_messages,
    search_messages,
)
from src.ui_state import current_memory_id, require_ragflow_key, set_memory_id

st.set_page_config(page_title="记忆 - My-RAG", page_icon="🧠", layout="wide")
st.title("🧠 记忆")

if not require_ragflow_key():
    st.stop()


def _load_memories():
    try:
        data = list_memories(page=1, page_size=100)
        if isinstance(data, dict):
            return data.get("memory_list") or data.get("data") or [], data.get("total_count", 0)
        return data or [], 0
    except RagflowError as e:
        st.error(f"加载记忆库失败：{e}")
        return [], 0


def _model_options(model_type: str) -> dict[str, str]:
    """{model_name@provider_instance: 显示文本}。建记忆库需要传 embd_id / llm_id。"""
    try:
        data = list_added_models(model_type=model_type)
        models = (data or {}).get("models") or []
    except RagflowError as e:
        st.warning(f"加载{model_type}模型失败：{e}")
        return {}
    opts: dict[str, str] = {}
    for m in models:
        if not isinstance(m, dict):
            continue
        name = m.get("model_name", "")
        inst = m.get("model_instance", "")
        prov = m.get("model_provider", "")
        key = f"{name}@{inst}" if inst else name
        label = f"{name}" + (f" ({prov}/{inst})" if inst else f" ({prov})" if prov else "")
        opts[key] = label
    return opts


# ---- 新建记忆库 ----
with st.expander("➕ 新建记忆库", expanded=False):
    embd_opts = _model_options("embedding")
    llm_opts = _model_options("chat")
    if not embd_opts or not llm_opts:
        st.info("需要先在 ragflow 后台添加 embedding 与 chat 模型，再回来建记忆库。")
    else:
        with st.form("new_memory", clear_on_submit=True):
            name = st.text_input("名称 *")
            mtypes = st.multiselect("记忆类型 *", MEMORY_TYPES, default=["raw"])
            embd_id = st.selectbox("embedding 模型 *", options=list(embd_opts.keys()),
                                   format_func=lambda k: embd_opts[k])
            llm_id = st.selectbox("LLM 模型 *", options=list(llm_opts.keys()),
                                  format_func=lambda k: llm_opts[k])
            desc = st.text_input("描述")
            policy = st.selectbox("遗忘策略", ["FIFO", "LRU"], index=0)
            if st.form_submit_button("创建") and name.strip() and mtypes and embd_id and llm_id:
                try:
                    create_memory(name=name, memory_type=mtypes, embd_id=embd_id,
                                  llm_id=llm_id, description=desc, forgetting_policy=policy)
                    st.success(f"已创建记忆库「{name}」")
                    st.rerun()
                except RagflowError as e:
                    st.error(f"创建失败：{e}")

st.divider()

# ---- 记忆库列表 ----
memories, total = _load_memories()
st.subheader(f"记忆库列表（共 {total}）")
if not memories:
    st.info("还没有记忆库，点上方新建。")

for mem in memories:
    if not isinstance(mem, dict):
        continue
    mid = mem.get("id", "")
    cols = st.columns([3, 2, 2, 2, 1, 1])
    cols[0].write(mem.get("name", ""))
    cols[1].write(",".join(mem.get("memory_type", []) or []))
    cols[2].write(mem.get("embd_id", ""))
    cols[3].write(mem.get("llm_id", ""))
    if cols[4].button("进入", key=f"enter_{mid}"):
        set_memory_id(mid)
        st.rerun()
    if cols[5].button("删除", key=f"del_{mid}", type="primary"):
        try:
            delete_memory(mid)
            if current_memory_id() == mid:
                set_memory_id("")
            st.rerun()
        except RagflowError as e:
            st.error(f"删除失败：{e}")

st.divider()

# ---- 进入某记忆库：消息管理 + 搜索 ----
mid = current_memory_id()
if not mid:
    st.stop()

st.subheader(f"记忆库消息（{mid[:8]}…）")

# 搜索
with st.form("search_mem"):
    q = st.text_input("搜索记忆", placeholder="输入查询语句")
    top_n = st.slider("top_n", 1, 20, 5)
    if st.form_submit_button("搜索") and q.strip():
        try:
            res = search_messages([mid], q, top_n=top_n)
            hits = res if isinstance(res, list) else (res or {}).get("messages", [])
            if not hits:
                st.info("无召回。")
            for i, h in enumerate(hits, 1):
                if not isinstance(h, dict):
                    continue
                with st.expander(f"[{i}] 相似度 {h.get('similarity', 0)} · {h.get('user_input', '')[:40]}"):
                    st.write(f"**用户**：{h.get('user_input', '')}")
                    st.write(f"**助手**：{h.get('agent_response', '')}")
                    st.caption(f"session={h.get('session_id', '')} · msg_id={h.get('id', '')}")
        except RagflowError as e:
            st.error(f"搜索失败：{e}")

st.divider()

# 消息列表
page = st.number_input("页码", min_value=1, value=1, step=1)
PAGE_SIZE = 20
try:
    res = list_memory_messages(mid, page=page, page_size=PAGE_SIZE)
    if isinstance(res, dict):
        msgs = res.get("messages") or res.get("data") or []
        msg_total = res.get("total_count", res.get("total", len(msgs)))
    else:
        msgs = res or []
        msg_total = len(msgs)
except RagflowError as e:
    st.error(f"加载消息失败：{e}")
    msgs, msg_total = [], 0

st.caption(f"共 {msg_total} 条，第 {page} 页")
for m in msgs:
    if not isinstance(m, dict):
        continue
    msg_id = m.get("id", "")
    with st.expander(f"{m.get('user_input', '')[:50]} · session {str(m.get('session_id', ''))[:8]}"):
        st.write(f"**用户**：{m.get('user_input', '')}")
        st.write(f"**助手**：{m.get('agent_response', '')}")
        st.caption(f"id={msg_id} · created={m.get('created_at', m.get('create_time', ''))} · status={m.get('status', '')}")
        if st.button("🗑️ 遗忘此消息", key=f"forget_{mid}_{msg_id}", type="primary"):
            try:
                forget_message(mid, int(msg_id))
                st.success("已遗忘")
                st.rerun()
            except (RagflowError, ValueError) as e:
                st.error(f"遗忘失败：{e}")

cp = st.columns([1, 1, 1])
if cp[0].button("上一页", disabled=page <= 1):
    st.rerun()
if cp[2].button("下一页", disabled=len(msgs) < PAGE_SIZE):
    st.rerun()
