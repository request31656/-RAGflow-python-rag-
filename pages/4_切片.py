"""切片页面：选知识库+文档 → 分页查看 chunk + 编辑/新增/删除。"""
from __future__ import annotations

import streamlit as st

from src.ragflow_api import (
    RagflowError,
    create_chunk,
    delete_chunks,
    list_chunks,
    list_datasets,
    list_documents,
    update_chunk,
)
from src.ui_state import current_dataset_id, current_document_id, require_ragflow_key, set_dataset_id, set_document_id

st.set_page_config(page_title="切片 - My-RAG", page_icon="✂️", layout="wide")
st.title("✂️ 切片管理")

if not require_ragflow_key():
    st.stop()


def _load_kbs():
    try:
        data = list_datasets(page=1, page_size=100)
        return data.get("kbs") or data.get("data") or []
    except RagflowError:
        return []


def _load_docs(dataset_id: str):
    try:
        data = list_documents(dataset_id, page=1, page_size=100)
        return data.get("docs") or data.get("data") or []
    except RagflowError:
        return []


kbs = _load_kbs()
if not kbs:
    st.info("还没有知识库。")
    st.stop()

kb_options = {kb["id"]: kb.get("name", kb["id"]) for kb in kbs}
cur_kb = current_dataset_id() or list(kb_options.keys())[0]
ds = st.selectbox("知识库", options=list(kb_options.keys()),
                   index=list(kb_options.keys()).index(cur_kb) if cur_kb in kb_options else 0,
                   format_func=lambda k: kb_options[k])
set_dataset_id(ds)

docs = _load_docs(ds)
if not docs:
    st.info("此知识库没有文档。")
    st.stop()

doc_options = {d["id"]: d.get("name", d["id"]) for d in docs}
cur_doc = current_document_id() or list(doc_options.keys())[0]
doc_sel = st.selectbox("文档", options=list(doc_options.keys()),
                       index=list(doc_options.keys()).index(cur_doc) if cur_doc in doc_options else 0,
                       format_func=lambda k: doc_options[k])
set_document_id(doc_sel)

st.divider()

# ---- 新增 chunk ----
with st.expander("➕ 新增 chunk", expanded=False):
    with st.form("new_chunk", clear_on_submit=True):
        content = st.text_area("内容")
        kws = st.text_input("重要关键词（逗号分隔）")
        if st.form_submit_button("新增") and content.strip():
            try:
                create_chunk(ds, doc_sel, content, [k.strip() for k in kws.split(",") if k.strip()])
                st.success("已新增")
                st.rerun()
            except RagflowError as e:
                st.error(f"新增失败：{e}")

# ---- chunk 列表 ----
page = st.number_input("页码", min_value=1, value=1, step=1)
PAGE_SIZE = 20
try:
    data = list_chunks(ds, doc_sel, page=page, page_size=PAGE_SIZE)
    chunks = data.get("chunks") or []
    total = data.get("total", len(chunks))
except RagflowError as e:
    st.error(f"加载切片失败：{e}")
    chunks, total = [], 0

st.subheader(f"切片列表（共 {total}，第 {page} 页）")
for i, c in enumerate(chunks):
    cid = c.get("id", "")
    content = c.get("content", "")
    page_num = c.get("page_num_int") or c.get("page") or 0
    if isinstance(page_num, list) and page_num:
        page_num = page_num[0]
    kws = c.get("important_keywords") or []

    with st.expander(f"[{cid[:8]}] 页{page_num} · 关键词{list(kws)} · {content[:40]}..."):
        new_content = st.text_area("内容", value=content, height=150, key=f"ed_{cid}")
        new_kws = st.text_input("重要关键词（逗号分隔）", value=",".join(kws), key=f"kw_{cid}")
        cc = st.columns(2)
        if cc[0].button("保存", key=f"save_{cid}"):
            try:
                update_chunk(ds, doc_sel, cid, content=new_content,
                             important_keywords=[k.strip() for k in new_kws.split(",") if k.strip()])
                st.success("已保存")
                st.rerun()
            except RagflowError as e:
                st.error(f"保存失败：{e}")
        if cc[1].button("🗑️ 删除", key=f"del_{cid}", type="primary"):
            try:
                delete_chunks(ds, doc_sel, [cid])
                st.rerun()
            except RagflowError as e:
                st.error(f"删除失败：{e}")

# 分页
cp = st.columns([1, 1, 1])
if cp[0].button("上一页", disabled=page <= 1):
    st.session_state["chunk_page"] = page - 1
    st.rerun()
if cp[2].button("下一页", disabled=len(chunks) < PAGE_SIZE):
    st.rerun()
