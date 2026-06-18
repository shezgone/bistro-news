"""모델 출력(JSON-ish) → 정규화 core_event 파서. (구 eval/_parse.py)

스프레드시트 붙여넣기·LLM 출력 모두 완전한 JSON이 아닐 때가 많아(중괄호 누락, 후행 콤마,
문자열 내 리터럴 개행, 주변 필드 오타, <think> 누출) 관대하게 복구한다. 파싱 실패/누출
자체가 품질 지표가 되므로, 여기서는 '복구 가능하면 복구'하되 원문(raw)은 그대로 보존한다.
"""
import json
import re

CORE_KEYS = ["who", "what", "when", "where", "why", "how",
             "event_type", "is_factual", "is_ongoing", "select_reason"]


def _try_json(text):
    """원문 → 후행콤마 제거 → 문자열 내 리터럴 개행을 공백으로, 순차 시도."""
    variants = [
        text,
        re.sub(r",(\s*[}\]])", r"\1", text),
        re.sub(r",(\s*[}\]])", r"\1", re.sub(r"[\n\r\t]+", " ", text)),
    ]
    for cand in variants:
        try:
            return json.loads(cand)
        except Exception:
            continue
    return None


def _extract_balanced(text, open_idx):
    """open_idx의 '{' 부터 균형 잡힌 객체 문자열 반환(문자열 리터럴 내 중괄호 무시)."""
    depth, in_str, esc = 0, False, False
    for i in range(open_idx, len(text)):
        ch = text[i]
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx:i + 1]
    return None


def _extract_core_event(text):
    """전체 파싱 실패 시 core_event 객체만 균형 중괄호로 떼어내 파싱(주변 오타에 강함)."""
    mkey = re.search(r'"core_event"\s*:\s*', text)
    if mkey:
        brace = text.find("{", mkey.end())
        if brace != -1:
            obj = _extract_balanced(text, brace)
            if obj:
                parsed = _try_json(obj)
                if isinstance(parsed, dict):
                    return parsed
    return None


def _coerce(v):
    if isinstance(v, str):
        s = v.strip()
        if s.upper() == "TRUE":
            return True
        if s.upper() == "FALSE":
            return False
        if s.lower() == "null":
            return None
    return v


def parse_core(raw):
    """셀/모델출력 원문 → (core_event dict | None, parse_status str)."""
    if raw is None or not str(raw).strip():
        return None, "empty"
    t = str(raw).strip()
    if t.lower() == "null":
        return None, "explicit_null"

    lines = [l.strip() for l in t.splitlines() if l.strip()]
    # 표 형태: 키 10줄 + 값 10줄
    if not t.startswith("{") and lines[:len(CORE_KEYS)] == CORE_KEYS and len(lines) >= 2 * len(CORE_KEYS):
        vals = lines[len(CORE_KEYS):2 * len(CORE_KEYS)]
        return {k: _coerce(v) for k, v in zip(CORE_KEYS, vals)}, "table"

    for cand, tag in ((t, "json"), ("{" + t + "}", "json_wrapped")):
        obj = _try_json(cand)
        if isinstance(obj, dict):
            if "core_event" in obj:
                return obj["core_event"], tag + "+core_event"
            return obj, tag + "+inner"

    core = _extract_core_event(t)
    if core is not None:
        return core, "core_event_salvaged"
    return None, "parse_error"
