"""ragflow HTTP API 薄封装。

后端能力（解析/检索/存储/对话/记忆）全交给 ragflow docker，本模块只做 HTTP 调用。
契约源：ragflow/api/apps/restful_apis/{chat,memory,models,chunk,document,dataset,file,search}_api.py
（SDK 参考 ragflow/sdk/python/ragflow_sdk/）。统一认证：Authorization: Bearer <RAGFLOW_API_KEY>。
ragflow 返回 {code, message, data}，code!=0 抛 RagflowError。

按 ragflow 五大核心业务模块分组：datasets / documents / chunks / files / retrieval / chats / sessions /
completion / memories / models。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

import httpx

from .config import settings
from .tracing import observe


class RagflowError(RuntimeError):
    """ragflow API 返回 code!=0 或 HTTP 非 2xx。"""


_BASE = settings.ragflow_base_url.rstrip("/")
_HEADERS = {"Authorization": f"Bearer {settings.ragflow_api_key}"}


def _check(resp: httpx.Response) -> Any:
    """统一解析 ragflow 响应：HTTP 非 2xx 或 code!=0 报错；返回 data。"""
    if resp.status_code != 200:
        raise RagflowError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    body = resp.json()
    # ragflow 多数接口返回 {code, message, data}；code==0 成功。
    if isinstance(body, dict) and "code" in body:
        if body.get("code") != 0:
            raise RagflowError(body.get("message") or f"ragflow error: {body}")
        return body.get("data")
    return body


def _get(path: str, **params) -> Any:
    resp = httpx.get(f"{_BASE}/api/v1{path}", headers=_HEADERS, params=params, timeout=120)
    return _check(resp)


def _post(path: str, json: dict | None = None, **kwargs) -> Any:
    resp = httpx.post(f"{_BASE}/api/v1{path}", headers=_HEADERS, json=json, timeout=600, **kwargs)
    return _check(resp)


def _put(path: str, json: dict | None = None) -> Any:
    resp = httpx.put(f"{_BASE}/api/v1{path}", headers=_HEADERS, json=json, timeout=120)
    return _check(resp)


def _delete(path: str, json: dict | None = None) -> Any:
    resp = httpx.delete(f"{_BASE}/api/v1{path}", headers=_HEADERS, json=json, timeout=120)
    return _check(resp)


def _patch(path: str, json: dict | None = None) -> Any:
    resp = httpx.patch(f"{_BASE}/api/v1{path}", headers=_HEADERS, json=json, timeout=120)
    return _check(resp)


# ============================ datasets（知识库）============================

CHUNK_METHODS = ["naive", "book", "email", "laws", "manual", "one", "paper", "picture", "presentation", "qa", "table", "tag"]


def list_datasets(page: int = 1, page_size: int = 30, keywords: str = "") -> Any:
    params = {"page": page, "page_size": page_size}
    if keywords:
        params["keywords"] = keywords
    return _get("/datasets", **params)


def get_dataset(dataset_id: str) -> Any:
    return _get(f"/datasets/{dataset_id}")


def create_dataset(name: str, description: str = "", embedding_model: str = "",
                   chunk_method: str = "naive", parser_config: dict | None = None,
                   permission: str = "me") -> Any:
    body: dict[str, Any] = {"name": name, "permission": permission, "chunk_method": chunk_method}
    if description:
        body["description"] = description
    if embedding_model:
        body["embedding_model"] = embedding_model
    if parser_config:
        body["parser_config"] = parser_config
    return _post("/datasets", json=body)


def update_dataset(dataset_id: str, **fields) -> Any:
    return _put(f"/datasets/{dataset_id}", json=fields)


def delete_datasets(dataset_ids: list[str]) -> Any:
    return _delete("/datasets", json={"ids": dataset_ids})


# ============================ documents（文档）============================

def list_documents(dataset_id: str, page: int = 1, page_size: int = 30,
                   keywords: str = "", name: str = "", id: str = "") -> Any:
    params = {"page": page, "page_size": page_size}
    if keywords:
        params["keywords"] = keywords
    if name:
        params["name"] = name
    if id:
        params["id"] = id
    return _get(f"/datasets/{dataset_id}/documents", **params)


@observe(name="upload_document")
def upload_document(dataset_id: str, file_path: Path) -> Any:
    """上传单个文档到知识库。返回 ragflow document 字段（含 id/name/run）。"""
    with file_path.open("rb") as f:
        files = {"file": (file_path.name, f)}
        # multipart 上传不能用 json=，headers 不要带 Content-Type（httpx 自动加 boundary）
        resp = httpx.post(
            f"{_BASE}/api/v1/datasets/{dataset_id}/documents",
            headers=_HEADERS, files=files, timeout=300,
        )
    data = _check(resp)
    # data 是 list，取匹配本次文件名的那项
    if isinstance(data, list):
        for d in data:
            if d.get("name") == file_path.name:
                return d
        return data[0] if data else {}
    return data


@observe(name="parse_documents")
def parse_documents(dataset_id: str, document_ids: list[str]) -> Any:
    return _post(f"/datasets/{dataset_id}/documents/parse", json={"document_ids": document_ids})


def stop_parse(dataset_id: str, document_ids: list[str]) -> Any:
    return _post(f"/datasets/{dataset_id}/documents/stop", json={"document_ids": document_ids})


def delete_documents(dataset_id: str, document_ids: list[str]) -> Any:
    return _delete(f"/datasets/{dataset_id}/documents", json={"ids": document_ids})


def update_document(dataset_id: str, document_id: str, **fields) -> Any:
    return _patch(f"/datasets/{dataset_id}/documents/{document_id}", json=fields)


def download_document(dataset_id: str, document_id: str) -> bytes:
    """下载文档原文，返回字节流。"""
    resp = httpx.get(
        f"{_BASE}/api/v1/datasets/{dataset_id}/documents/{document_id}",
        headers=_HEADERS, timeout=300,
    )
    if resp.status_code != 200:
        raise RagflowError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.content


# ============================ chunks（切片）============================

def list_chunks(dataset_id: str, document_id: str, page: int = 1, page_size: int = 30,
                keywords: str = "") -> Any:
    params = {"page": page, "page_size": page_size}
    if keywords:
        params["keywords"] = keywords
    return _get(f"/datasets/{dataset_id}/documents/{document_id}/chunks", **params)


def get_chunk(dataset_id: str, document_id: str, chunk_id: str) -> Any:
    return _get(f"/datasets/{dataset_id}/documents/{document_id}/chunks/{chunk_id}")


def create_chunk(dataset_id: str, document_id: str, content: str,
                 important_keywords: list[str] | None = None) -> Any:
    body: dict[str, Any] = {"content": content}
    if important_keywords:
        body["important_keywords"] = important_keywords
    return _post(f"/datasets/{dataset_id}/documents/{document_id}/chunks", json=body)


def update_chunk(dataset_id: str, document_id: str, chunk_id: str, **fields) -> Any:
    return _patch(f"/datasets/{dataset_id}/documents/{document_id}/chunks/{chunk_id}", json=fields)


def delete_chunks(dataset_id: str, document_id: str, chunk_ids: list[str]) -> Any:
    return _delete(f"/datasets/{dataset_id}/documents/{document_id}/chunks", json={"ids": chunk_ids})


# ============================ files（user 文件空间）============================

def list_files(parent_id: str = "", page: int = 1, page_size: int = 30, keywords: str = "") -> Any:
    params = {"page": page, "page_size": page_size}
    if parent_id:
        params["parent_id"] = parent_id
    if keywords:
        params["keywords"] = keywords
    return _get("/files", **params)


def upload_file(file_path: Path, parent_id: str = "") -> Any:
    with file_path.open("rb") as f:
        files = {"file": (file_path.name, f)}
        data = {"parent_id": parent_id} if parent_id else None
        resp = httpx.post(f"{_BASE}/api/v1/files", headers=_HEADERS, files=files, data=data, timeout=300)
    return _check(resp)


def delete_files(file_ids: list[str]) -> Any:
    return _delete("/files", json={"ids": file_ids})


def move_files(src_file_ids: list[str], dest_file_id: str = "", new_name: str = "") -> Any:
    body: dict[str, Any] = {"src_file_ids": src_file_ids}
    if dest_file_id:
        body["dest_file_id"] = dest_file_id
    if new_name:
        body["new_name"] = new_name
    return _post("/files/move", json=body)


def create_folder(name: str, parent_id: str = "") -> Any:
    body: dict[str, Any] = {"name": name}
    if parent_id:
        body["parent_id"] = parent_id
    return _post("/files", json=body)


def download_file(file_id: str) -> bytes:
    resp = httpx.get(f"{_BASE}/api/v1/files/{file_id}", headers=_HEADERS, timeout=300)
    if resp.status_code != 200:
        raise RagflowError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.content


def link_to_datasets(file_ids: list[str], kb_ids: list[str]) -> Any:
    """把 user 文件空间的文件移入知识库（生成 document）。"""
    return _post("/files/link-to-datasets", json={"file_ids": file_ids, "kb_ids": kb_ids})


# ============================ retrieval（检索）============================

@observe(name="retrieval")
def search(question: str, dataset_ids: list[str], top_k: int | None = None,
           similarity_threshold: float | None = None, vector_similarity_weight: float | None = None,
           rerank_id: str = "") -> Any:
    """检索，返回 {total, chunks[], doc_aggs}。chunks 含 content/document_keyword/page_num_int/similarity。"""
    body: dict[str, Any] = {
        "dataset_ids": dataset_ids,
        "question": question,
        "top_k": top_k or settings.top_k,
        "similarity_threshold": similarity_threshold or settings.similarity_threshold,
        "vector_similarity_weight": vector_similarity_weight or settings.vector_similarity_weight,
    }
    if rerank_id:
        body["rerank_id"] = rerank_id
    return _post("/retrieval", json=body)


# ============================ chats（对话助手）============================

def list_chats(page: int = 1, page_size: int = 30, name: str = "", id: str = "",
               keywords: str = "") -> Any:
    params = {"page": page, "page_size": page_size}
    if name:
        params["name"] = name
    if id:
        params["id"] = id
    if keywords:
        params["keywords"] = keywords
    return _get("/chats", **params)


def get_chat(chat_id: str) -> Any:
    return _get(f"/chats/{chat_id}")


def create_chat(name: str, dataset_ids: list[str], description: str = "", llm_id: str = "",
                prompt_config: dict | None = None, **extra) -> Any:
    """创建对话助手。dataset_ids 必填：本系统始终绑定知识库做 RAG 问答。"""
    body: dict[str, Any] = {"name": name, "dataset_ids": dataset_ids}
    if description:
        body["description"] = description
    if llm_id:
        body["llm_id"] = llm_id
    if prompt_config:
        body["prompt_config"] = prompt_config
    body.update(extra)
    return _post("/chats", json=body)


def update_chat(chat_id: str, **fields) -> Any:
    return _put(f"/chats/{chat_id}", json=fields)


def patch_chat(chat_id: str, **fields) -> Any:
    return _patch(f"/chats/{chat_id}", json=fields)


def delete_chats(ids: list[str]) -> Any:
    return _delete("/chats", json={"ids": ids})


# ============================ sessions（会话）============================

def list_sessions(chat_id: str, page: int = 1, page_size: int = 30) -> Any:
    return _get(f"/chats/{chat_id}/sessions", page=page, page_size=page_size)


def create_session(chat_id: str, name: str = "New session") -> Any:
    return _post(f"/chats/{chat_id}/sessions", json={"name": name})


def get_session(chat_id: str, session_id: str) -> Any:
    return _get(f"/chats/{chat_id}/sessions/{session_id}")


def update_session(chat_id: str, session_id: str, name: str) -> Any:
    return _patch(f"/chats/{chat_id}/sessions/{session_id}", json={"name": name})


def delete_sessions(chat_id: str, ids: list[str]) -> Any:
    return _delete(f"/chats/{chat_id}/sessions", json={"ids": ids})


# ============================ completion（流式问答）============================

@observe(name="chat_completion")
def chat_completions(chat_id: str, session_id: str, question: str,
                     stream: bool = True, **extra) -> Iterator[dict]:
    """调 /chat/completions，流式产出 {answer, reference, done}。

    ragflow SSE 每行 `data:{json}\\n\\n`：json.data==True 为结束哨兵；否则 data.answer 为增量、
    data.reference.chunks 为引用（最后一块才完整）。非流式返回单条 dict。
    """
    body: dict[str, Any] = {
        "chat_id": chat_id,
        "session_id": session_id,
        "question": question,
        "stream": stream,
    }
    body.update(extra)

    if not stream:
        data = _post("/chat/completions", json=body)
        yield {"answer": (data or {}).get("answer", ""), "reference": (data or {}).get("reference", {}), "done": True}
        return

    # 流式：手动发 httpx 流式请求，绕过 _check（SSE 不是 {code,message,data} 信封）
    with httpx.stream("POST", f"{_BASE}/api/v1/chat/completions",
                      headers=_HEADERS, json=body, timeout=600) as resp:
        if resp.status_code != 200:
            raise RagflowError(f"HTTP {resp.status_code}: {resp.read().decode(errors='replace')[:200]}")
        for line in resp.iter_lines():
            if not line:
                continue
            line = line.strip()
            if line.startswith("data:"):
                line = line[len("data:"):].strip()
            if not line or line == "[DONE]":
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            code = payload.get("code", 0)
            if code != 0:
                raise RagflowError(payload.get("message") or f"ragflow stream error: {payload}")
            data = payload.get("data")
            if data is True:  # 结束哨兵
                yield {"answer": "", "reference": {}, "done": True}
                return
            if not isinstance(data, dict):
                continue
            yield {
                "answer": data.get("answer", ""),
                "reference": data.get("reference", {}) or {},
                "done": False,
            }


# ============================ memories（记忆）============================

MEMORY_TYPES = ["raw", "fact", "theme", "tool", "relationship"]


def list_memories(page: int = 1, page_size: int = 50, memory_type: str = "",
                  keywords: str = "") -> Any:
    params = {"page": page, "page_size": page_size}
    if memory_type:
        params["memory_type"] = memory_type
    if keywords:
        params["keywords"] = keywords
    return _get("/memories", **params)


def create_memory(name: str, memory_type: list[str], embd_id: str, llm_id: str,
                  description: str = "", forgetting_policy: str = "FIFO") -> Any:
    body: dict[str, Any] = {
        "name": name,
        "memory_type": memory_type,
        "embd_id": embd_id,
        "llm_id": llm_id,
    }
    if description:
        body["description"] = description
    if forgetting_policy:
        body["forgetting_policy"] = forgetting_policy
    return _post("/memories", json=body)


def update_memory(memory_id: str, **fields) -> Any:
    return _put(f"/memories/{memory_id}", json=fields)


def delete_memory(memory_id: str) -> Any:
    return _delete(f"/memories/{memory_id}")


def get_memory_config(memory_id: str) -> Any:
    return _get(f"/memories/{memory_id}/config")


def list_memory_messages(memory_id: str, page: int = 1, page_size: int = 50,
                         keywords: str = "") -> Any:
    """列出某记忆库内的消息（user_input/agent_response）。"""
    params = {"page": page, "page_size": page_size}
    if keywords:
        params["keywords"] = keywords
    return _get(f"/memories/{memory_id}", **params)


def forget_message(memory_id: str, message_id: int) -> Any:
    return _delete(f"/messages/{memory_id}:{message_id}")


def update_message_status(memory_id: str, message_id: int, status: bool) -> Any:
    return _put(f"/messages/{memory_id}:{message_id}", json={"status": status})


def search_messages(memory_ids: list[str], query: str, top_n: int = 5,
                    similarity_threshold: float = 0.2,
                    keywords_similarity_weight: float = 0.7) -> Any:
    """在记忆库里检索相关消息。GET /messages/search。"""
    return _get("/messages/search", memory_id=",".join(memory_ids), query=query,
                top_n=top_n, similarity_threshold=similarity_threshold,
                keywords_similarity_weight=keywords_similarity_weight)


def add_message(memory_ids: list[str], agent_id: str, session_id: str,
                user_input: str, agent_response: str, user_id: str = "") -> Any:
    """显式向记忆库写入一条对话消息（本系统不在聊天中自动调用）。"""
    body = {
        "memory_id": memory_ids,
        "agent_id": agent_id,
        "session_id": session_id,
        "user_input": user_input,
        "agent_response": agent_response,
    }
    if user_id:
        body["user_id"] = user_id
    return _post("/messages", json=body)


# ============================ models（模型清单，供记忆建库选模型）============================

def list_added_models(model_type: str = "") -> Any:
    """列出租户已添加的模型。model_type: chat/embedding/rerank/asr/vision/tts/ocr。"""
    params = {}
    if model_type:
        params["type"] = model_type
    return _get("/models", **params)


def list_default_models() -> Any:
    return _get("/models/default")
