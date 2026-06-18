"""2. LLM 4-step 이벤트 추출 (Step A Core → B Background → C Consequence → D Critic).

기사 + prompts/step_*.md → 모델 호출 → 구조화 이벤트(event_schema.json).
"""
from .pipeline import run_legacy, run_new4step

__all__ = ["run_legacy", "run_new4step"]
