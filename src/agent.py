"""对话编排：基于 ragflow chat assistant + session 的流式问答。

不做 LangGraph。agent.ask() 是生成器：逐块产出 (delta_text, reference)，
最后一块产出完整 reference（ragflow 在流末才给出完整引用）。
记忆与聊天解耦：本模块不读写记忆库，记忆独立在 pages/7_记忆.py 管理。
"""
from __future__ import annotations

from typing import Iterator

from .ragflow_api import chat_completions


def ask(chat_id: str, session_id: str, question: str, **extra) -> Iterator[tuple[str, dict]]:
    """流式问答。

    yield (delta_text, reference)。delta_text 是本轮增量回答片段，reference 在末块为完整引用
    （含 chunks/doc_aggs），中间块 reference 为空 dict——页面只需在循环结束后用最后一份渲染引用。
    """
    last_reference: dict = {}
    for chunk in chat_completions(chat_id, session_id, question, stream=True, **extra):
        if chunk.get("done"):
            if last_reference:
                yield "", last_reference
            return
        delta = chunk.get("answer", "")
        ref = chunk.get("reference", {})
        if ref:
            last_reference = ref
        if delta:
            yield delta, ref
