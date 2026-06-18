"""LLM 공용: 모델 클라이언트(client) + 프롬프트 로더(prompts)."""
from .client import call_model
from .prompts import fill, load_prompt

__all__ = ["call_model", "fill", "load_prompt"]
