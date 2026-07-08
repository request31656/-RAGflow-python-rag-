"""RAGAS 评测（占位，非核心功能）。

精简版只保留五大核心（知识库/聊天/记忆/搜索/文件管理），评测不在其中。
如需启用：用 ragflow /retrieval + /chat/completions 跑出 (answer, contexts)，
再引入 ragas 评测。当前为占位。
"""
from __future__ import annotations


def main() -> None:
    raise NotImplementedError("评测为非核心功能，当前未启用；详见模块文档。")
