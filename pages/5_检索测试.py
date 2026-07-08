"""检索测试页面：选知识库 + 输入问题 → /retrieval → 展示 chunks + 来源聚合。"""
from __future__ import annotations

import streamlit as st

from src.ragflow_api import RagflowError, list_datasets, search
from src.ui_state import current_dataset_id, require_ragflow_key, set_dataset_id

st.set_page_config(page_title="检索测试 - My-RAG", page_icon="🔎", layout="wide")
st.title("🔎 检索测试")

if not require_ragflow_key():
    st.stop()


def _load_kbs():
    try:
        data = list_datasets(page=1, page_size=100)
        return data.get("kbs") or data.get("data") or []
    except RagflowError:
        return []


kbs = _load_kbs()
if not kbs:
    st.info("还没有知识库。")
    st.stop()

kb_options = {kb["id"]: kb.get("name", kb["id"]) for kb in kbs}
cur = current_dataset_id() or list(kb_options.keys())[0]
selected = st.selectbox("选择知识库", options=list(kb_options.keys()),
                        index=list(kb_options.keys()).index(cur) if cur in kb_options else 0,
                        format_func=lambda k: kb_options[k])
set_dataset_id(selected)

question = st.text_input("问题", placeholder="输入要检索的问题")
top_k = st.slider("top_k", 1, 50, 10)

if st.button("检索") and question.strip():
    try:
        with st.spinner("检索中…"):
            data = search(question, [selected], top_k=top_k)
        chunks = data.get("chunks") or []
        doc_aggs = data.get("doc_aggs") or {}
        total = data.get("total", len(chunks))

        st.success(f"召回 {total} 条，展示 {len(chunks)} 条")

        if doc_aggs:
            st.subheader("来源文档聚合")
            for doc_id, agg in (doc_aggs.items() if isinstance(doc_aggs, dict) else []):
                st.write(f"- {agg.get('doc_name', doc_id)}：{agg.get('count', 0)} 条")

        st.subheader("检索结果")
        for i, c in enumerate(chunks, 1):
            sim = c.get("similarity", 0)
            doc = c.get("document_keyword", c.get("docnm_kwd", ""))
            page = c.get("page_num_int") or c.get("page") or 0
            if isinstance(page, list) and page:
                page = page[0]
            content = c.get("content", "")
            with st.expander(f"[{i}] 相似度 {sim:.3f} · {doc} · 页{page}"):
                st.write(content)
                kws = c.get("important_keywords") or []
                if kws:
                    st.caption(f"关键词：{list(kws)}")
    except RagflowError as e:
        st.error(f"检索失败：{e}")
