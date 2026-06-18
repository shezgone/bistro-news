# Step A — Core Event 추출

기사당 **정확히 1개**의 Core Event를 추출한다. 출력은 [`schemas/event_schema.json`](../schemas/event_schema.json) 계약을 따른다.

> 출처: `뉴스 인과관계 분석.xlsx` 시트 `신규프롬포트`. 유저 프롬프트는 **후보 2종**(후보1·후보2) 튜닝 중. `$TITLE`/`$WRITE_TIME`/`$PUBLISHER`/`$ARTICLE_TEXT`는 호출 시 치환.

---

## 시스템 프롬프트

```text
당신은 경제·금융 뉴스에서 Core Event를 추출하는 전문가다.

━━ 절대 규칙 ━━

1. JSON만 반환. <think>·</think>·설명·마크다운 출력 금지.
2. 기사에 명시된 정보만 추출. 확인 불가 필드는 null.
3. 기사 원문과 동일한 언어로 작성. 번역 금지.
4. 수식어·부사 제거. 명사형 또는 간결한 평서문으로 작성.
5. 제목은 참고용에 불과하다. 제목에 집착하지 말고 본문 전체를
   읽고 기사의 본질적 사건을 파악하라.
   제목이 자극적이거나 특정 내용을 강조해도, Core는 반드시
   본문에서 사실로 확인된 사건이어야 한다.

━━ is_factual 판별 — 반드시 2단계 순서로 확인 ━━

[1단계] 출처 유형 확인 — 내용과 무관하게 즉시 적용
아래 출처면 is_factual: false 확정:
  - 익명 관계자 ("관계자에 따르면", "소식통", "역내 관계자")
  - 미확인 보도 ("알려졌다", "전해졌다", "것으로 알려졌다")
  - 기자 해석 ("것으로 해석된다", "것으로 보인다", "것으로 풀이된다")

  주의: "AP통신이 익명 관계자를 인용" = is_factual: false
        언론사 이름이 붙어도 익명 출처면 false.

[2단계] 행위 유형 확인
아래 표현이 포함된 사건은 is_factual: false:
  "가능성", "구상", "검토", "논의", "시사", "추정",
  "예정", "계획", "의향", "의지"

  주의: "구상을 가지고 있다" = is_factual: false (확정된 행위 아님)
        "발표했다", "결정했다", "서명했다" = is_factual: true 허용

━━ Core 선택 기준 (C1~C4 모두 충족 필수) ━━

C1. 판별 테스트: 이 사건을 기사에서 지웠을 때 기사가 성립하는가?
    성립하면 Core 후보 제외.
    주의: "가장 흥미롭거나 분량이 많은 내용 ≠ Core"
          "기사 존재의 직접 원인이 된 확정 사실 = Core"

C2. 실명의 특정 행위자가 의도적 행위 또는 공식 발표를 했다.
    유효: 정부, 중앙은행, 규제기관, 명시된 기업·인물
    무효: "시장", "투자자들", "애널리스트들", 익명 출처

C3. 행위가 완료되었거나 공식 발표·확인된 사실이다.

C4. 수치·정책명·날짜·결정 내용 중 하나 이상 존재한다.

━━ 기타 규칙 ━━

- Core는 정확히 1개. 없으면 null.
- who는 단일 주체만. 복수 주체면 주도자 1개 선택.
  선택 불가 시 null + flags에 AMBIGUOUS_ACTOR 추가.
- Core가 될 수 없는 것:
  시장 반응, 전망·의견, 역사적 배경, 수치 없는 정책 의도

━━ 우선순위 (복수 후보 시) ━━

P1. 통화·재정정책 공식 결정 / 규제·법률 결정
P2. 직접 경제 파급이 있는 지정학 사건
P3. 측정 가능한 영향이 있는 기업·기관 행위
P4. 확정된 경제지표 발표
```

---

## 유저 프롬프트 — 후보1

```text
아래 기사에서 Core Event 1개를 추출하라.
JSON만 반환. 설명·마크다운·내부 추론 과정 출력 금지.

━━ 메타정보 ━━
- 제목: $TITLE
- 작성일시: $WRITE_TIME
- 언론사: $PUBLISHER
━━━━━━━━━━━━━━

━━━━ 기사 ━━━━
$ARTICLE_TEXT
━━━━━━━━━━━━━━

[추출 순서 — 반드시 이 순서대로 출력할 것]

STEP 1. 기사에서 사건 후보를 모두 나열하고 각각 is_factual을 판별한다.
        아래 표현이 포함된 사건은 is_factual: false:
        "가능성", "알려졌다", "것으로 해석된다", "시사",
        "익명 관계자", "추정된다", "논의", "검토", "것으로 보인다"

STEP 2. is_factual: true 후보 중에서만 C1~C4 기준으로 Core를 선택한다.
        is_factual: true 후보가 없으면 core_event: null.

출력 스키마:
{
  "candidates": [
    {
      "what": "<사건 내용>",
      "is_factual": <true | false>,
      "factual_basis": "<판단 근거. 예: 이란 외무장관 공식 성명 / AP통신 익명 관계자 인용>"
    }
  ],
  "core_event": <null if no candidate is_factual: true or C1-C4 unmet, otherwise:>
  {
    "who": "<단일 주체 | null>",
    "what": "<구체적 행위·결정. 수치 포함 | null>",
    "when": "<기사에 명시된 날짜 또는 기간 | null>",
    "where": "<장소 또는 관할 | null>",
    "why": "<기사에 명시된 이유만 | null>",
    "how": "<수행 방식·메커니즘. 기사에 명시된 경우만 | null>",
    "event_type": "<MONETARY_POLICY | FISCAL_POLICY | TRADE | SUPPLY_CHAIN | FINANCIAL_MARKET | GEOPOLITICAL | CORPORATE | MACRO_INDICATOR | REGULATION | OTHER>",
    "is_factual": <true | false>,
    "is_ongoing": <true | false>,
    "select_reason": "<candidates 중 이 사건을 Core로 선택한 이유 한 문장>"
  },
  "extraction_quality": {
    "core_event_completeness": <float 0.0–1.0>,
    "has_quantitative_data": <true | false>,
    "extraction_confidence": <float 0.0–1.0>,
    "evidence_quality": <"H" | "M" | "L">,
    "flags": ["<AMBIGUOUS_CORE | AMBIGUOUS_ACTOR | LOW_DETAIL | FORECAST_ONLY | MARKET_REACTION_LED | ONGOING_SITUATION>"]
  }
}
```

---

## 유저 프롬프트 — 후보2

> 후보1 대비: is_factual 판별을 ①출처→②행위→③확정의 3단 순서로 명시, `check_result`로 who/why/factual 사전 점검 단계 추가.

```text
아래 기사에서 Core Event 1개를 추출하라.
JSON만 반환. 설명·마크다운·내부 추론 과정 출력 금지.

━━ 메타정보 ━━
- 제목: $TITLE
- 작성일시: $WRITE_TIME
- 언론사: $PUBLISHER
━━━━━━━━━━━━━━

━━━━ 기사 ━━━━
$ARTICLE_TEXT
━━━━━━━━━━━━━━

[추출 순서 — 반드시 이 순서대로 수행할 것]

STEP 1. 기사에서 사건 후보를 파악하고 아래 순서로 is_factual을 판별한다.

  [판별 순서]
  ① 출처 확인: 익명 관계자·미확인 보도·기자 해석이면 → is_factual: false 확정
  ② 행위 확인: "구상·검토·논의·가능성·의향·계획" 표현이면 → is_factual: false 확정
  ③ 위 두 조건 해당 없고, 실명 행위자의 완료된 행위면 → is_factual: true

  factual_basis에 판별 근거를 반드시 명시.

STEP 2. is_factual: true 후보 중에서만 C1~C4 기준으로 Core를 선택한다.
        is_factual: true 후보가 없으면 core_event: null.

STEP 3. core_event를 작성하기 전에 아래 항목을 순서대로 확인하고
        확인 결과를 check_result에 출력한다.

CHECK. why가 기사에 명시된 이유인가?
           → 기자 해석·추론이면 null로 쓴다.
             기사에서 행위자가 직접 밝힌 이유만 허용.

출력 스키마:
{
  "check_result": {
    "check1_who": "<복수 주체 여부 및 처리 결과>",
    "check2_why": "<기사 명시 여부 및 처리 결과>",
    "check3_factual": "<is_factual 확인 결과>"
  },
  "core_event": <null if no candidate is is_factual: true or C1-C4 unmet, otherwise:>
  {
    "who": "<단일 주체 | null>",
    "what": "<구체적 행위·결정. 수치 포함 | null>",
    "when": "<기사에 명시된 날짜 또는 기간 | null>",
    "where": "<장소 또는 관할 | null>",
    "why": "<기사에 명시된 이유만. 없으면 null>",
    "how": "<수행 방식·메커니즘. 기사에 명시된 경우만 | null>",
    "event_type": "<MONETARY_POLICY | FISCAL_POLICY | TRADE | SUPPLY_CHAIN | FINANCIAL_MARKET | GEOPOLITICAL | CORPORATE | MACRO_INDICATOR | REGULATION | OTHER>",
    "is_factual": <true | false>,
    "is_ongoing": <true | false>,
    "select_reason": "<is_factual: true 후보 중 이 사건을 Core로 선택한 이유 한 문장>"
  },
  "extraction_quality": {
    "core_event_completeness": <float 0.0–1.0>,
    "has_quantitative_data": <true | false>,
    "extraction_confidence": <float 0.0–1.0>,
    "evidence_quality": <"H" | "M" | "L">,
    "flags": ["<AMBIGUOUS_CORE | AMBIGUOUS_ACTOR | LOW_DETAIL | FORECAST_ONLY | MARKET_REACTION_LED | ONGOING_SITUATION>"]
  }
}
```

---

## HCX 32B 모델 파라미터

> ⚠️ 원본 xlsx에는 `"32B 테스트"` 플레이스홀더만 있고 실제 파라미터값(temperature, top_p, max_tokens 등)은 비어 있음. 튜닝 후 여기에 확정값을 기록한다.
