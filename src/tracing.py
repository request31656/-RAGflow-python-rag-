"""Langfuse tracing 接入。

v3 的 @observe 装饰器在 import 时即生效，但需要 Langfuse 单例初始化后才会真正
上报；未配置 public/secret key 时跳过初始化，装饰器退化为透传（不报错、不阻断），
simple 模式 / 离线环境照样能跑。

用法：在要 trace 的函数上 `from src.tracing import observe` + `@observe(name=...)`。
app.py 启动时 import 本模块一次即完成单例初始化。
"""
from __future__ import annotations

from .config import settings

try:
    from langfuse import Langfuse
    from langfuse.decorators import observe as _lf_observe

    _LF_AVAILABLE = True
except Exception:  # langfuse 未装或依赖缺失 → 降级
    Langfuse = None  # type: ignore[assignment]
    _lf_observe = None  # type: ignore[assignment]
    _LF_AVAILABLE = False


def _maybe_init() -> None:
    """配置齐全才初始化单例；否则什么都不做。"""
    if not _LF_AVAILABLE:
        return
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return
    Langfuse(  # type: ignore[misc]
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def observe(fn=None, *, name: str | None = None):
    """包一层 langfuse @observe：可用时装饰，否则原样返回。

    支持 @observe 和 @observe(name="...") 两种写法。
    """
    if not _LF_AVAILABLE:
        return fn if fn is not None else (lambda f: f)

    decorator = _lf_observe(name=name) if name else _lf_observe()
    return decorator(fn) if fn is not None else decorator


_maybe_init()
