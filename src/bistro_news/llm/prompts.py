"""prompts/step_*.md 로더 + 변수 치환.

prompts/ 의 `## 시스템 프롬프트` / `## 유저 프롬프트…` 헤딩 아래 ```...``` 펜스 블록을 읽는다.
"""
import re
from pathlib import Path
from string import Template

# src/bistro_news/llm/prompts.py → repo/prompts
DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


def _blocks_by_heading(md):
    """`## 제목` 아래 ```...``` 펜스 블록들을 {제목: [블록,...]} 으로."""
    out, cur, buf = {}, None, None
    for line in md.splitlines():
        h = re.match(r"^##\s+(.*)", line)
        if h:
            cur = h.group(1).strip()
            continue
        if line.startswith("```"):
            if buf is None:
                buf = []
            else:
                out.setdefault(cur, []).append("\n".join(buf))
                buf = None
            continue
        if buf is not None:
            buf.append(line)
    return out


def load_prompt(filename, user_heading_contains=None, prompts_dir=None):
    """prompts/<filename> → (system, user). user_heading_contains 로 후보 선택."""
    base = Path(prompts_dir) if prompts_dir else DEFAULT_PROMPTS_DIR
    blocks = _blocks_by_heading((base / filename).read_text(encoding="utf-8"))
    system = next((v[0] for k, v in blocks.items() if "시스템" in k and v), None)
    user = None
    for k, v in blocks.items():
        if "유저" not in k or not v:
            continue
        if user_heading_contains and user_heading_contains not in k:
            continue
        user = v[0]
        if user_heading_contains:
            break
    if user is None:  # 후보 못 찾으면 첫 유저 블록
        user = next((v[0] for k, v in blocks.items() if "유저" in k and v), None)
    if not system or not user:
        raise ValueError(f"{filename}: 시스템/유저 프롬프트 블록을 찾지 못함")
    return system, user


def fill(template_str, **kw):
    """$TITLE 등 placeholder 치환 (없는 변수는 그대로 둠)."""
    return Template(template_str).safe_substitute(**kw)
