"""모델 클라이언트 — 의존성 없음(stdlib urllib). 자격증명은 env 로만.

backend:
  - anthropic      : POST {base}/v1/messages         (x-api-key, anthropic-version)
  - openai_compat  : POST {base}/v1/chat/completions  (Authorization: Bearer) — 사내 게이트웨이 다수가 호환
cfg = models.json 의 한 설정 (backend/model/api_key_env/base_url_env/max_tokens/temperature...).
"""
import json
import os
import urllib.request


def _post(url, headers, payload, timeout=180):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _env(name, required=True):
    v = os.environ.get(name)
    if required and not v:
        raise SystemExit(f"환경변수 {name} 미설정 — models.json 참조")
    return v


def call_model(cfg, system, user):
    backend = cfg["backend"]
    if backend == "anthropic":
        base = os.environ.get(cfg.get("base_url_env", ""), "") or "https://api.anthropic.com"
        body = {"model": cfg["model"], "max_tokens": cfg.get("max_tokens", 2000),
                "system": system, "messages": [{"role": "user", "content": user}]}
        if "temperature" in cfg:
            body["temperature"] = cfg["temperature"]
        resp = _post(base.rstrip("/") + "/v1/messages",
                     {"x-api-key": _env(cfg["api_key_env"]), "anthropic-version": "2023-06-01"}, body)
        return "".join(b.get("text", "") for b in resp.get("content", []))
    if backend == "openai_compat":
        base = _env(cfg["base_url_env"])
        key = os.environ.get(cfg.get("api_key_env", ""), "")
        body = {"model": cfg["model"],
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
        for k in ("temperature", "top_p", "max_tokens"):
            if k in cfg:
                body[k] = cfg[k]
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        resp = _post(base.rstrip("/") + "/v1/chat/completions", headers, body)
        return resp["choices"][0]["message"]["content"]
    raise SystemExit(f"알 수 없는 backend: {backend}")
