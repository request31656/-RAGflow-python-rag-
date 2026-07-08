"""知识库页面：列表 + 新建 + 删除。"""
from __future__ import annotations

import streamlit as st

from src.ragflow_api import CHUNK_METHODS, RagflowError, create_dataset, delete_datasets, list_datasets
from src.ui_state import require_ragflow_key, set_dataset_id

st.set_page_config(page_title="知识库 - My-RAG", page_icon="📚", layout="wide")
st.title("📚 知识库")

if not require_ragflow_key():
    st.stop()


def _load(page: int = 1) -> dict:
    try:
        return list_datasets(page=page, page_size=30)
    except RagflowError as e:
        st.error(f"加载失败：{e}")
        return {"total": 0, "kbs": []}


# ---- 新建知识库 ----
with st.expander("➕ 新建知识库", expanded=False):
    with st.form("create_kb", clear_on_submit=True):
        name = st.text_input("名称 *")
        desc = st.text_area("描述")
        chunk_method = st.selectbox("切片方法", CHUNK_METHODS, index=0,
                                    help="naive=通用, book=书籍, manual=手册, qa=问答对, paper=论文, table=表格, ...")
        embedding_model = st.text_input("embedding 模型（留空用租户默认）")
        submitted = st.form_submit_button("创建")
        if submitted:
            if not name.strip():
                st.error("名称必填")
            else:
                try:
                    create_dataset(name=name, description=desc, embedding_model=embedding_model,
                                    chunk_method=chunk_method)
                    st.success(f"已创建知识库「{name}」")
                    st.rerun()
                except RagflowError as e:
                    st.error(f"创建失败：{e}")

st.divider()

# ---- 知识库列表 ----
data = _load()
kbs = data.get("kbs") or data.get("data") or []
total = data.get("total", len(kbs))

st.subheader(f"知识库列表（共 {total}）")
if not kbs:
    st.info("还没有知识库，点上方「新建」。")

cols_header = st.columns([3, 2, 2, 1, 1, 1])
for c, h in zip(cols_header, ["名称", "切片方法", "embedding", "文档数", "chunk数", "操作"]):
    c.caption(h)

for kb in kbs:
    cols = st.columns([3, 2, 2, 1, 1, 1])
    cols[0].write(kb.get("name", ""))
    cols[1].write(kb.get("chunk_method", ""))
    cols[2].write(kb.get("embedding_model", ""))
    cols[3].write(str(kb.get("document_count", kb.get("doc_num", 0))))
    cols[4].write(str(kb.get("chunk_num", 0)))
    kid = kb.get("id", "")
    with cols[5]:
        c1, c2 = st.columns(2)
        if c1.button("进入", key=f"enter_{kid}"):
            set_dataset_id(kid)
            st.switch_page("pages/3_文档.py")
        if c2.button("删除", key=f"del_{kid}", type="primary"):
            try:
                delete_datasets([kid])
                st.success("已删除")
                st.rerun()
            except RagflowError as e:
                st.error(f"删除失败：{e}")
