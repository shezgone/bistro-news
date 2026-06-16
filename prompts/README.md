# Prompts — 이벤트 추출 프롬프트

기사를 구조화 이벤트로 바꾸는 LLM 프롬프트 모음. **기획팀 주 작업 영역.**
출력은 항상 `schemas/event_schema.json` 계약을 따라야 한다.

## 신규안 = 4-step 분할

| Step | 역할 | 핵심 규칙 |
|---|---|---|
| **A. Core** | 핵심 사건 1개 추출 | 기사당 정확히 1개. `is_factual`은 **출처 유형 먼저 판별**(익명/미확인/기자해석 → false) |
| **B. Background** | 선행 원인·배경 | Core보다 시간상 먼저. 시간단서 우선 → 선행표현("~으로 인해") → 불가 시 제외 |
| **C. Consequence** | 후속 결과·영향 | 예측·전망 허용. 확정 과거사실은 Background로. 추론은 낮은 confidence |
| **D. Quality Critic** | A·B·C 병합 + 품질평가 | 원칙적으로 무수정, 명확한 오류만 교정(미래형↔과거사실 이동, Core 2개→1개 등) |

> 기존안은 단일 프롬프트 1회 호출. 신규안이 이를 4개 호출로 분할해 정확도를 높이려는 실험.

## 작업 규칙

- 단계별 파일로 관리 (예: `step_a_core.md`, `step_b_background.md`, …). 모델별 변형은 접미사로(`step_a_core.hcx32b.md`).
- 프롬프트 변경 시 **변경 이유**를 커밋 메시지에 남길 것.
- 출력 필드/enum을 바꾸려면 `schemas/event_schema.json`을 **먼저** 합의·수정한 뒤 프롬프트를 맞춘다.
- 비교 모델: HCX-007 / HCX 32B / Claude Sonnet 4.6 / Gemini 3.1 Pro. 목표 = 저비용 HCX 32B로 Claude 수준 달성.

## TODO
- [ ] events.pptx·`뉴스 인과관계 분석.xlsx`의 프롬프트 원문을 단계별 파일로 이관
- [ ] 정량 평가셋 구축(현재 기사 2건 정성평가뿐) — 필드 정확도·core 1개 준수율·is_factual 오류율
