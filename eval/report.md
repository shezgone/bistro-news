# BISTRO-News — 이벤트 추출 품질 평가 (core 중심)

> 자동 생성: `python eval/score.py`. 기사 5건 (xlsx 인제스트 + 수집).
> **⚠️ 커버리지: reference(Opus) 5건 / HCX-32B 2건.** HCX 측은 게이트웨이 연결 시 확장 — 현재 1:1 비교 가능 구간은 2건. 통계적 결론 아님.
> reference = `ref_claude4step` (Claude Opus, 4-step). Sonnet 미사용. 현재 reference 는 Opus 부트스트랩(자가생성) — 정식화 시 독립 API Opus 로 교체.

## 핵심 가설 답: 신규 4-step HCX-32B 가 Claude Opus(4-step) reference 에 도달하는가?

| 설정 | 모델 | 프롬프트 | core 1개 추출 | core 주제 정답 | is_factual 정답 | event_type enum | 누출無 | 한글enum無 | **종합 합격** | Claude 일치 |
|---|---|---|---|---|---|---|---|---|---|---|
| `ref_claude4step` | Claude (Opus 4.8, bootstrap) | 신규 4-step | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **5/5** 🟢 | 5/5 |
| `new4step_hcx32b` | HCX-32B | 신규 4-step | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | **2/2** 🟢 | 2/2 |
| `legacy_claude_sonnet46` | Claude Sonnet 4.6 | 기존 단일 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | **2/2** 🟢 | 2/2 |
| `legacy_hcx32b_think` | HCX-32B(Think) | 기존 단일 | 2/2 | 1/2 | 1/2 | 1/2 | 1/2 | 1/2 | **0/2** 🔴 | 1/2 |
| `legacy_hcx007` | HCX-007 | 기존 단일 | 1/2 | 0/2 | 0/2 | 1/2 | 2/2 | 2/2 | **0/2** 🔴 | 0/2 |

w5h1 평균 충실도: `ref_claude4step`=0.93, `new4step_hcx32b`=1.00, `legacy_claude_sonnet46`=1.00, `legacy_hcx32b_think`=1.00, `legacy_hcx007`=0.50

## 기사별 상세

### bok_rate_hold_20260410 — 한은 4월 기준금리 연 2.50% 동결

| 설정 | parse_ok | core_extracted | event_type_valid | no_leak | no_kr_enum | core_topic_correct | is_factual_correct | claude_agreement | core_quality_pass | w5h1 |
|---|---|---|---|---|---|---|---|---|---|---|
| `ref_claude4step` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 0.83 |

### cpi_may_20260602 — 2026년 5월 소비자물가 전년동월비 3.1% 상승

| 설정 | parse_ok | core_extracted | event_type_valid | no_leak | no_kr_enum | core_topic_correct | is_factual_correct | claude_agreement | core_quality_pass | w5h1 |
|---|---|---|---|---|---|---|---|---|---|---|
| `ref_claude4step` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 0.83 |

### hormuz_toll_20260408 — 호르무즈 통행료 체계 / 美·이란 휴전

| 설정 | parse_ok | core_extracted | event_type_valid | no_leak | no_kr_enum | core_topic_correct | is_factual_correct | claude_agreement | core_quality_pass | w5h1 |
|---|---|---|---|---|---|---|---|---|---|---|
| `ref_claude4step` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1.00 |
| `new4step_hcx32b` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1.00 |
| `legacy_claude_sonnet46` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1.00 |
| `legacy_hcx32b_think` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 1.00 |
| `legacy_hcx007` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 1.00 |

### semicon_tariff_20260118 — 미국 100% 관세 압박 / 반도체 추가투자 요구

| 설정 | parse_ok | core_extracted | event_type_valid | no_leak | no_kr_enum | core_topic_correct | is_factual_correct | claude_agreement | core_quality_pass | w5h1 |
|---|---|---|---|---|---|---|---|---|---|---|
| `ref_claude4step` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1.00 |

### transit_tf_20260408 — 출퇴근 혼잡완화 범정부 TF 발족

| 설정 | parse_ok | core_extracted | event_type_valid | no_leak | no_kr_enum | core_topic_correct | is_factual_correct | claude_agreement | core_quality_pass | w5h1 |
|---|---|---|---|---|---|---|---|---|---|---|
| `ref_claude4step` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1.00 |
| `new4step_hcx32b` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1.00 |
| `legacy_claude_sonnet46` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1.00 |
| `legacy_hcx32b_think` | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | 1.00 |
| `legacy_hcx007` | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 0.00 |
