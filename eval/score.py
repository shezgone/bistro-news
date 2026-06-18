#!/usr/bin/env python3
"""
predictions/*.json + gold/gold.json → core 추출 품질 지표 → report.md + stdout.

핵심 가설: 저비용 신규 4-step HCX-32B 가 Claude Sonnet 4.6(기존 단일프롬프트) 급 추출 품질에 도달하는가?

지표 두 계열 (사용자 결정: 둘 다):
  [A] 기준점 불요 — 자동 객관 지표
      - parse_ok            : core 셀이 구조화 객체로 파싱됨
      - core_extracted      : core_event 가 null 아님
      - event_type_valid    : event_type ∈ 스키마 enum
      - w5h1_completeness   : who/what/when/where/why/how 비-null 비율
      - no_leak             : <think>/영어 지시문 누출 없음
      - no_kr_enum          : event_type/consequence_type/time_horizon/relation 값에 한글 enum 위반 없음
  [B] gold 기준 (수작업 2건) — 품질 정오
      - core_topic_correct  : 선택한 core 주제가 gold 인정 주제와 일치
      - is_factual_correct  : core 의 is_factual 이 규칙상 옳음(특히 비사실 사건을 core+true 로 오선택하지 않음)
  + claude_agreement        : core 정오 결과가 Claude Sonnet 4.6 설정과 동일 버킷인가

'core_quality_pass' = parse_ok ∧ core_extracted ∧ core_topic_correct ∧ is_factual_correct
                      ∧ event_type_valid ∧ no_leak ∧ no_kr_enum   (한 출력의 종합 합격)

⚠️ n=2. 통계적 결론 아님. 방향성 신호 + 재현 가능한 채점 절차 제공이 목적.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRED_DIR = HERE / "predictions"
GOLD = json.loads((HERE / "gold" / "gold.json").read_text(encoding="utf-8"))["articles"]
REPORT = HERE / "report.md"

EVENT_TYPE_ENUM = {"MONETARY_POLICY", "FISCAL_POLICY", "TRADE", "SUPPLY_CHAIN",
                   "FINANCIAL_MARKET", "GEOPOLITICAL", "CORPORATE", "MACRO_INDICATOR",
                   "REGULATION", "OTHER"}
W5H1 = ["who", "what", "when", "where", "why", "how"]

LEAK_RE = re.compile(r"</?think>|formulate the answer|as an ai|i (?:cannot|will)", re.I)
KR_ENUM_RE = re.compile(r'"(?:event_type|consequence_type|time_horizon|relation_to_core)"\s*:\s*"[가-힣]')

# going-forward reference = Claude Opus, 4-step (Sonnet 미사용 확정). 없으면 과거 Sonnet 데이터로 폴백.
REFERENCE_CFG = "ref_claude4step"
# 출력 표 정렬 순서 (reference·경쟁자 우선, 과거 데이터는 뒤로)
CONFIG_ORDER = ["ref_claude4step", "new4step_hcx32b",
                "legacy_claude_sonnet46", "legacy_hcx32b_think", "legacy_hcx007"]


def _txt(core, *keys):
    return " ".join(str(core.get(k) or "") for k in keys)


def score_one(rec):
    core = rec["core_event"]
    block = rec.get("raw_block") or ""
    gold = GOLD[rec["article_id"]]["core"]
    m = {}

    m["parse_ok"] = rec["parse_status"] not in ("parse_error", "empty")
    m["core_extracted"] = core is not None
    m["no_leak"] = not bool(LEAK_RE.search(block))
    m["no_kr_enum"] = not bool(KR_ENUM_RE.search(block))

    if core is None:
        m["event_type_valid"] = False
        m["w5h1_completeness"] = 0.0
        m["core_topic_correct"] = False
        # core 없음: 비사실 사건을 사실 core 로 오선택하진 않았으나 '정답 사건'을 놓침 → 정오 실패로 본다
        m["is_factual_correct"] = False
        m["_picked_rejected"] = False
    else:
        et = core.get("event_type")
        m["event_type_valid"] = et in EVENT_TYPE_ENUM
        m["w5h1_completeness"] = round(
            sum(1 for k in W5H1 if core.get(k) not in (None, "")) / len(W5H1), 3)

        what_reason = _txt(core, "what", "select_reason")
        accepted = any(kw in what_reason for kw in gold["accepted_topic_keywords"])
        # core 가 '거부 대상' 사건을 집어 들었는가
        picked_rejected = False
        rejected_factual_violation = False
        for rj in gold.get("rejected_as_core", []):
            if any(kw in _txt(core, "what") for kw in rj["topic_keywords"]):
                picked_rejected = True
                # 거부 사건을 core 로 두고 is_factual=true 로 표기 → 규칙 위반
                if core.get("is_factual") is True and rj["correct_is_factual"] is False:
                    rejected_factual_violation = True
        m["_picked_rejected"] = picked_rejected
        m["core_topic_correct"] = bool(accepted and not picked_rejected)
        # is_factual 정오: 거부사건 오선택+true 가 아니고, 정답 core 면 is_factual==gold
        if rejected_factual_violation:
            m["is_factual_correct"] = False
        elif m["core_topic_correct"]:
            m["is_factual_correct"] = (core.get("is_factual") == gold["is_factual"])
        else:
            m["is_factual_correct"] = False

    m["core_quality_pass"] = all([
        m["parse_ok"], m["core_extracted"], m["core_topic_correct"],
        m["is_factual_correct"], m["event_type_valid"], m["no_leak"], m["no_kr_enum"],
    ])
    return m


def main():
    preds = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(PRED_DIR.glob("*.json"))]
    if not preds:
        raise SystemExit("predictions 없음 — 먼저 `python eval/extract_from_xlsx.py` 실행.")

    scored = {}  # config_id -> list of (article_id, metrics, model)
    by_art_cfg = {}  # (article, config) -> metrics
    for rec in preds:
        m = score_one(rec)
        scored.setdefault(rec["config_id"], []).append((rec["article_id"], m, rec["model"]))
        by_art_cfg[(rec["article_id"], rec["config_id"])] = m

    # ref_agreement: 각 출력의 core_topic_correct 가 같은 기사 reference(Claude Opus 4-step)와 동일한가
    ref_cfg = REFERENCE_CFG if any(c == REFERENCE_CFG for _, c in by_art_cfg) else "legacy_claude_sonnet46"
    for (art, cfg), m in by_art_cfg.items():
        rm = by_art_cfg.get((art, ref_cfg))
        m["claude_agreement"] = (rm is not None and m["core_topic_correct"] == rm["core_topic_correct"])

    bool_cols = ["parse_ok", "core_extracted", "event_type_valid", "no_leak", "no_kr_enum",
                 "core_topic_correct", "is_factual_correct", "claude_agreement", "core_quality_pass"]
    lines = []
    p = lines.append
    ref_n = len(scored.get("ref_claude4step", []))
    hcx_n = len(scored.get("new4step_hcx32b", []))
    n_articles = len({a for a, _ in by_art_cfg})
    p("# BISTRO-News — 이벤트 추출 품질 평가 (core 중심)\n")
    p(f"> 자동 생성: `python eval/score.py`. 기사 {n_articles}건 (xlsx 인제스트 + 수집).")
    p(f"> **⚠️ 커버리지: reference(Opus) {ref_n}건 / HCX-32B {hcx_n}건.** HCX 측은 게이트웨이 연결 시 확장 — 현재 1:1 비교 가능 구간은 {hcx_n}건. 통계적 결론 아님.")
    p("> reference = `ref_claude4step` (Claude Opus, 4-step). Sonnet 미사용. 현재 reference 는 Opus 부트스트랩(자가생성) — 정식화 시 독립 API Opus 로 교체.\n")
    p("## 핵심 가설 답: 신규 4-step HCX-32B 가 Claude Opus(4-step) reference 에 도달하는가?\n")

    def agg(cfg, key):
        vals = [m[key] for _, m, _ in scored[cfg]]
        if all(isinstance(v, bool) for v in vals):
            return f"{sum(vals)}/{len(vals)}"
        return f"{sum(vals) / len(vals):.2f}"

    model_of = {cfg: scored[cfg][0][2] for cfg in scored}
    fam_of = {rec["config_id"]: rec["family"] for rec in preds}

    # 요약 표
    p("| 설정 | 모델 | 프롬프트 | core 1개 추출 | core 주제 정답 | is_factual 정답 | event_type enum | 누출無 | 한글enum無 | **종합 합격** | Claude 일치 |")
    p("|---|---|---|---|---|---|---|---|---|---|---|")
    for cfg in CONFIG_ORDER:
        if cfg not in scored:
            continue
        fam = "신규 4-step" if fam_of[cfg] == "new_4step" else "기존 단일"
        passes = [m["core_quality_pass"] for _, m, _ in scored[cfg]]
        star = "🟢" if all(passes) else ("🟡" if any(passes) else "🔴")
        p(f"| `{cfg}` | {model_of[cfg]} | {fam} | {agg(cfg,'core_extracted')} | "
          f"{agg(cfg,'core_topic_correct')} | {agg(cfg,'is_factual_correct')} | "
          f"{agg(cfg,'event_type_valid')} | {agg(cfg,'no_leak')} | {agg(cfg,'no_kr_enum')} | "
          f"**{agg(cfg,'core_quality_pass')}** {star} | {agg(cfg,'claude_agreement')} |")
    p("")
    p("w5h1 평균 충실도: " + ", ".join(
        f"`{cfg}`={sum(m['w5h1_completeness'] for _,m,_ in scored[cfg])/len(scored[cfg]):.2f}"
        for cfg in CONFIG_ORDER if cfg in scored))
    p("")

    # 기사별 상세
    p("## 기사별 상세\n")
    arts = sorted({a for a, _ in by_art_cfg})
    for art in arts:
        title = GOLD[art]["title"] if art in GOLD else art
        p(f"### {art} — {title}\n")
        p("| 설정 | " + " | ".join(bool_cols) + " | w5h1 |")
        p("|" + "---|" * (len(bool_cols) + 2))
        for cfg in CONFIG_ORDER:
            m = by_art_cfg.get((art, cfg))
            if not m:
                continue
            cells = ["✅" if m[c] else "❌" for c in bool_cols]
            p(f"| `{cfg}` | " + " | ".join(cells) + f" | {m['w5h1_completeness']:.2f} |")
        p("")

    report = "\n".join(lines)
    REPORT.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n→ {REPORT}")


if __name__ == "__main__":
    main()
