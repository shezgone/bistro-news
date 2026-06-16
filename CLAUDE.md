# BISTRO-News

거시경제 모델 구축을 위한 **뉴스 기반 인과관계 분석** 프로젝트.
뉴스 기사에서 구조화된 경제·금융 이벤트를 추출하고, 이벤트 간 선후·인과관계 그래프를 만들어
금융/실물 거시지표(ECOS)와 비교하는 시계열 인과 분석을 목표로 한다.

## 파이프라인

권위 스펙 = 기획팀 문서 **"Track 2. 뉴스 인과관계 파이프라인 분석"** (고객 events.pptx를 구현 수준으로 구체화). 아래는 그 요약이며, 충돌 시 기획팀 문서가 우선.

1. **뉴스 수집 & 중복 제거** — (1) 기사 본문 SHA256 해시로 완전 동일 기사 제거, (2) **BGE-M3**(BAAI) 임베딩으로 유사 기사 클러스터링, `cluster_uuid`로 묶어 관리.

2. **LLM 기반 Event Extraction (신규 = 4-step 분할 프롬프트)** — 한 번에 뽑지 않고 단계별 추출. (기존안 = 단일 프롬프트 1회 호출; 신규안이 이를 4개 호출로 분할.)
   - **Step A — Core Event** — 기사당 **정확히 1개**. "기사가 작성된 직접적 원인" 사건을 5W1H로. 2개 이상 나오면 재호출. 제목 아닌 본문 사실 기준. `is_factual`은 **2단계**로 판별: ①출처 유형 먼저(익명 관계자/미확인 보도/기자 해석 → `false` 확정) → ②내용 판단. (HCX 32B용 모델 파라미터·유저 프롬프트 후보 2종 튜닝 중.)
   - **Step B — Background Events** — Step A Core를 컨텍스트로 전달, "이 사건이 일어나기 위해 선행된 원인". 시간적으로 Core보다 **먼저**여야 함. 시간 단서 우선 → 없으면 선행 표현("~으로 인해", "~가 누적되어") → 판단 불가 시 제외.
   - **Step C — Consequence Events** — Core 이후 예상 후속 영향. 예측·전망·우려 표현("~할 것으로 보인다", "~될 전망"). 확정된 과거 사실이 섞이면 Background로 재분류. 추론은 낮은 confidence + `is_stated_in_article:false`.
   - **Step D — Quality Critic** — A·B·C 결과 **병합** + 3차원 품질평가. 원칙적으로 수정 없이 점수·flags만 추가하되, 명확한 오류는 교정: ①Background에 미래형 → Consequence로 이동, ②Consequence에 확정 과거사실 → Background로 이동, ③Core 2개 이상 → 우선순위(P1→P4)로 1개만, ④"가능성·검토·추정"인데 `is_factual:true` → `false`, ⑤who 복수 → 주도 주체 1개.
   - 공통 출력: 유효한 JSON만 (`core_event` / `background_events` / `consequence_events` / `entities` / `extraction_quality`). `<think>` 등 내부 추론 토큰 출력 금지, 사실/추론 분리, 원문 언어 유지.

3. **Event Clustering** — 추출 이벤트를 다시 임베딩해 유사도 검증, **같은 계열 이벤트끼리** 클러스터링.

4. **Event Propagation Graph (인과 그래프)** — 노드 = 이벤트(5W1H + 타입 + event_type), 엣지 = 방향성 가중 인과관계. 시간 방향이 강제되어 구조적으로 DAG에 가깝다.

   **엣지 생성 경로 = 2가지 (둘 다 사용)**
   - **① 기사 내 (intra-article)**: 한 기사의 `background → core → consequence`. **이벤트 추출(Step A/B/C)이 직접 생성.** consequence는 대개 예측·추론(`is_stated_in_article`, 낮은 confidence).
   - **② 기사 간 (inter-article)**: 기사 A의 consequence(예측) ↔ 기사 B의 core(사실)를 **클러스터링(임베딩 유사도)이 같은 이벤트로 매칭**해 연결. **이게 핵심 가치** — "예측된 결과"가 나중 기사에서 "실제 사건(`is_factual=true`)"으로 실현되는 기사 경계 너머의 인과 사슬을 추적. (예: 호르무즈 휴전·통행료 → 중동발 고유가[공유 노드] → 범정부 교통TF 발족.)

   **⚠️ 병합 규칙 (구현 전 합의 필수)**: ② 에서 consequence(예측)와 core(사실)가 매칭될 때 —
   - (a) **한 노드로 병합**: 단순하지만 "예측→실현" 전환 시점 정보 소실.
   - (b) **별도 노드 + `REALIZED_AS` 엣지** (권장): 정보 풍부, "언제 예측이 맞았나" 추적 가능 → lead-lag·예측 검증에 유리.
   - `is_factual`/`confidence` 충돌 처리 규칙과 노드 정의(이벤트 vs 엔티티/event_type 레이어)를 함께 확정한다.

   **edge 검증 = 3단계 필터링** (위 ①②로 생긴 후보 엣지에 적용):
   - **Phase 1 — 시간 방향성 강제 (Gate 1)**: `Background → Core → Consequence` 시간 순서 강제, 역방향 화살표 원천 차단. 동일 날짜 등 시간 중첩은 보류 후 Phase 3에서 통계 검증.
   - **Phase 2 — 3요소 가중치**: 통과 후보 edge에 `가중치 = 시간 선행성 점수 × 의미 유사도(BGE-M3 코사인) × 보도 빈도 점수`. 임계값(예 0.3) 미만 제거.
   - **Phase 3 — Spurious 링크 이중 검증**: ① **LLM CRITIC** 재검증("두 이벤트 사이 경제적 인과관계가 존재하는가? 예/아니오 + 근거"), ② **PCMCI** 시계열 통계 교차 검증(뉴스 인과 그래프 vs 실제 거시지표 시계열의 통계적 인과 비교). 둘 다 통과한 edge만 최종 그래프에 포함.

5. **인덱스화 → 시계열 연계** — 수백 개 이벤트를 일별 인덱스(숫자)로 압축:
   - **Track B (메인)**: 그래프 **eigenvector centrality** 일별 계산 → 전날 대비 변화량(Δcentrality) 집계를 인덱스로. "연쇄 파급력이 큰 이벤트"가 높은 값. 방법론 출처 = Tilly & Livan, *Macroeconomic forecasting with statistically validated knowledge graphs*, arXiv:2104.10457 (2021-04-21; Expert Systems with Applications 게재). 뉴스 narrative로 theme 지식그래프 구성 → 통계적 유의 edge "backbone" 필터링 → 노드 eigenvector centrality 변화로 3개 대형 경제권 산업생산 예측력 개선. **검증 완료**.
   - **Track A (baseline)**: 이벤트 클러스터별 일별 기사 수 × 미디어 중요도 가중합. 구현이 쉬워 Track B 검증용 베이스라인.

6. **역방향 검증 루프** — 소규모 실행 → 예측 오차로 스펙 확정: ① 기존 시계열 모델(ARIMA/LSTM)에 Track A/B 인덱스 추가 투입해 오차(MSE/MAE) 비교 → ② **Granger 인과 검정**(인덱스가 경제지표보다 선행하는지) → ③ **lead-lag 구조** 파악(예: 공급망 이벤트는 T+2주 후 물가 반영) → ④ 결과를 거슬러 그래프 edge 가중치·클러스터링 기준까지 재조정.

## LLM IE 성능 비교 (실험 현황)

원본 데이터: `뉴스 인과관계 분석.xlsx` (구글시트 다운로드) — 시트 3개: `기존 프롬포트`(단일 프롬프트), `신규프롬포트`(Step A/B/C/D), `간이 비교 평가`.

- **핵심 가설**: 저비용·로컬 **HCX 32B**를 신규 4-step 프롬프트로 돌리면 **Claude Sonnet 4.6**(기존 단일 프롬프트) 수준 추출 품질에 도달 가능한가.
- **비교군**: 기존 프롬포트 × {HCX-007, HCX 32B(Think), Claude Sonnet 4.6} vs 신규 4-step × HCX 32B. (고객 events.pptx엔 Gemini 3.1 Pro도 등장.)
- **평가 상태**: 현재는 기사 2건(호르무즈 통행료 / 범정부 TF)에 대한 **정성 "간이" 비교**뿐 — 점수화·정량 벤치마크 아님. 모델 선정 결론을 내기 전 더 많은 기사 + 정량 지표(필드 정확도, core 1개 준수율, is_factual 오류율 등) 필요.
- AI 호출은 사내 LLM 게이트웨이(엔드포인트는 내부 설정 참조)와 Anthropic/HCX API 사용.

## 데이터 출처

- 뉴스 기사 (원문 언어 유지, 번역 금지).
- 거시지표: **ECOS API** (`ecos.bok.or.kr`, 공개 경제통계) — CPI, 소비자동향(CSI) 등.

## 핵심 방법론·구현체

| 단계 | 방법 | 구현체(권장) | 상태 |
|---|---|---|---|
| 임베딩/클러스터링 | BGE-M3 | `BAAI/bge-m3` (HuggingFace `sentence-transformers`/`FlagEmbedding`) | 교과서 표준 |
| 그래프 중심성 | eigenvector centrality | `networkx.eigenvector_centrality` | 표준 |
| 시계열 인과 교차검증 | PCMCI | `tigramite` (Runge et al.) | 프런티어 |
| 선행성 통계 검정 | Granger causality | `statsmodels.tsa.stattools.grangercausalitytests` | 표준 |

- **참고문헌(검증 완료)**: 기획팀이 인용한 "UCL/Tilly(2021)" = Sonja Tilly & Giacomo Livan (UCL), *Macroeconomic forecasting with statistically validated knowledge graphs*, arXiv:2104.10457 (2021-04-21), Expert Systems with Applications 게재. Track B(eigenvector centrality)·Phase 3(통계적 edge 검증) 설계의 직접적 근거 논문.

## graphify

This project has (or will have) a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## 하네스 관찰 로깅

`.claude/settings.json`의 PreToolUse/PostToolUse 훅이 모든 툴 호출을 `.claude/harness-log.py`로
넘겨 `.claude/harness.log`에 한 줄씩 기록한다 (loop/하네스 동작 관찰용). `harness.log`는 git 추적 제외.
