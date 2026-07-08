"""文档管理页面：选知识库 → 文档列表 + 上传 + 解析 + 停止 + 删除 + 下载。"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

import streamlit as st

from src.ragflow_api import (
    RagflowError,
    delete_documents,
    download_document,
    list_datasets,
    list_documents,
    parse_documents,
    stop_parse,
    upload_document,
)
from src.ui_state import current_dataset_id, require_ragflow_key, set_document_id, set_dataset_id

st.set_page_config(page_title="文档 - My-RAG", page_icon="📄", layout="wide")
st.title("📄 文档管理")

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
    except RagflowError as e:
        st.error(f"加载文档失败：{e}")
        return []


# ---- 选择知识库 ----
kbs = _load_kbs()
if not kbs:
    st.info("还没有知识库，先去「知识库」页建一个。")
    st.stop()

kb_options = {kb["id"]: kb.get("name", kb["id"]) for kb in kbs}
cur = current_dataset_id() or list(kb_options.keys())[0]
cols = st.columns([3, 1])
selected = cols[0].selectbox("选择知识库", options=list(kb_options.keys()),
                             index=list(kb_options.keys()).index(cur) if cur in kb_options else 0,
                             format_func=lambda k: kb_options[k])
if cols[1].button("刷新"):
    st.rerun()
set_dataset_id(selected)

# ---- 上传文档到当前知识库 ----
with st.expander("⬆️ 上传文档到此知识库", expanded=False):
    up = st.file_uploader("选择文件", accept_multiple_files=True, key="doc_uploader")
    if up and st.button("上传"):
        for f in up:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(f.name).suffix) as tmp:
                tmp.write(f.getvalue())
                try:
                    upload_document(selected, Path(tmp.name))
                    st.success(f"已上传：{f.name}")
                except RagflowError as e:
                    st.error(f"{f.name} 上传失败：{e}")
        st.rerun()

st.divider()

# ---- 文档列表 ----
docs = _load_docs(selected)
st.subheader(f"文档列表（共 {len(docs)}）")
if not docs:
    st.info("此知识库还没有文档。")

for d in docs:
    did = d.get("id", "")
    name = d.get("name", "")
    run = d.get("run", "")
    progress = d.get("progress", 0)
    chunk_num = d.get("chunk_count", d.get("chunk_num", 0))
    token_num = d.get("token_count", d.get("token_num", 0))

    cols = st.columns([3, 2, 1, 1, 1, 1, 1])
    cols[0].write(name)
    cols[1].write(f"状态：{run}")
    cols[2].progress(min(int(progress) / 100, 100) if progress else 0)
    cols[3].write(f"chunk {chunk_num}")
    cols[4].write(f"token {token_num}")

    if cols[5].button("解析", key=f"parse_{did}"):
        try:
            parse_documents(selected, [did])
            st.success("已触发解析")
            st.rerun()
        except RagflowError as e:
            st.error(f"解析失败：{e}")
    if run == "RUNNING" and cols[6].button("停止", key=f"stop_{did}"):
        try:
            stop_parse(selected, [did])
            st.rerun()
        except RagflowError as e:
            st.error(f"停止失败：{e}")

    sub = st.columns([1, 1, 1, 1])
    if sub[0].button("查看切片", key=f"chunks_{did}"):
        set_document_id(did)
        st.switch_page("pages/4_切片.py")
    if sub[1].button("下载原文", key=f"dl_{did}"):
        try:
            blob = download_document(selected, did)
            st.download_button("下载", data=blob, file_name=name, key=f"dlbtn_{did}")
        except RagflowError as e:
            st.error(f"下载失败：{e}")
    if sub[2].button("重新解析", key=f"reparse_{did}"):
        try:
            parse_documents(selected, [did])
            st.rerun()
        except RagflowError as e:
            st.error(f"失败：{e}")
    if sub[3].button("🗑️ 删除", key=f"del_{did}", type="primary"):
        try:
            delete_documents(selected, [did])
            st.rerun()
        except RagflowError as e:
            st.error(f"删除失败：{e}")
    st.divider()

# 解析中的文档自动轮询（页面级，最多等 30 轮）
running = [d for d in docs if d.get("run") == "RUNNING"]
if running:
    time.sleep(3)
    st.rerun()
