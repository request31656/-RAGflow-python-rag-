"""文件管理页面：user 文件空间，上传/删除/移入知识库。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from src.ragflow_api import RagflowError, delete_files, list_datasets, list_files, link_to_datasets, upload_file
from src.ui_state import require_ragflow_key

st.set_page_config(page_title="文件 - My-RAG", page_icon="📁", layout="wide")
st.title("📁 文件管理")

if not require_ragflow_key():
    st.stop()


def _load_files(page: int = 1):
    try:
        return list_files(page=page, page_size=30)
    except RagflowError as e:
        st.error(f"加载失败：{e}")
        return {"total": 0, "files": []}


def _load_kbs():
    try:
        data = list_datasets(page=1, page_size=100)
        return data.get("kbs") or data.get("data") or []
    except RagflowError:
        return []


# ---- 上传 ----
with st.expander("⬆️ 上传文件", expanded=False):
    up = st.file_uploader("选择文件", accept_multiple_files=True)
    if up and st.button("上传到文件空间"):
        for f in up:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(f.name).suffix) as tmp:
                tmp.write(f.getvalue())
                try:
                    upload_file(Path(tmp.name))
                    st.success(f"已上传：{f.name}")
                except RagflowError as e:
                    st.error(f"{f.name} 上传失败：{e}")
        st.rerun()

st.divider()

# ---- 文件列表 ----
data = _load_files()
files = data.get("files") or data.get("data") or []
total = data.get("total", len(files))

st.subheader(f"文件列表（共 {total}）")
if not files:
    st.info("文件空间为空，上传几个文件试试。")

kbs = _load_kbs()
kb_options = {kb["id"]: kb["name"] for kb in kbs if kb.get("id")}

for f in files:
    fid = f.get("id", "")
    fname = f.get("name", "")
    cols = st.columns([4, 2, 1, 2, 1])
    cols[0].write(fname)
    cols[1].write(f.get("type", ""))
    cols[2].write(str(f.get("size", 0)))
    target = cols[3].selectbox("移入知识库", options=list(kb_options.keys()),
                               format_func=lambda k: kb_options[k], key=f"mv_{fid}")
    if cols[4].button("移入", key=f"link_{fid}") and target:
        try:
            link_to_datasets([fid], [target])
            st.success(f"已将「{fname}」移入「{kb_options[target]}」（去文档页解析）")
        except RagflowError as e:
            st.error(f"移入失败：{e}")
    if st.button("🗑️ 删除", key=f"del_{fid}"):
        try:
            delete_files([fid])
            st.rerun()
        except RagflowError as e:
            st.error(f"删除失败：{e}")
    st.divider()
