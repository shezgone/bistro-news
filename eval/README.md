# eval/ — 이벤트 추출 품질 정량 평가

핵심 가설을 **재현 가능한 숫자**로 답하기 위한 채점 파이프라인.

> **핵심 가설**: 저비용·로컬 **신규 4-step HCX-32B** 가 **Claude Opus(신규 4-step) reference** 수준 추출 품질에 도달하는가?

**전략(확정)**: Sonnet 미사용. **Claude Opus 를 신규 4-step 으로 "정주행"해 reference 코퍼스**를 만들고, **HCX-32B(신규 4-step)** 를 그에 비교한다. Claude·HCX 가 동일 프롬프트라 모델 변수만 격리된다. 과거 4중 비교(HCX-007/Think/Sonnet)는 이미 결론(legacy HCX 탈락)이라 곁가지로만 보존.

지금까지는 기사 2건에 대한 정성 "간이" 비교뿐이었다. 이 디렉터리는 그 비교를 자동 채점으로 바꾼다. **현재 데이터 = 기사 2건(n=2)** 이라 결론이 아니라 **방향성 신호 + 절차**다.

## 실행

```bash
# 채점 (xlsx 없이 재현 — predictions/ + gold/ 만 읽음)
python eval/score.py

# 기사 늘리기 (러너로 모델 호출 → predictions 생성)
cp eval/models.example.json eval/models.json   # 1) 백엔드 설정(시크릿은 env 로)
python eval/run_extraction.py --dry-run         # 2) 호출 없이 프롬프트 렌더링 검증
python eval/run_extraction.py                   # 3) 4개 설정 호출 → predictions/*.json
python eval/score.py                            # 4) 채점

# (초기 2건은 xlsx 에서 인제스트됨 — 재현용)
python eval/extract_from_xlsx.py
```

`score.py` 는 버전관리되는 `predictions/` + `gold/` 만 읽으므로 **원본 없이도 재현**된다.
`run_extraction.py` 는 의존성 없음(stdlib). `extract_from_xlsx.py` 만 `openpyxl` + 원본 xlsx 필요.

## 구조

```
eval/
├── articles/<id>.json     # 기사 입력 {article_id,title,write_time,publisher,body} (gitignore)
├── run_extraction.py      # 모델 호출 CLI — 추출 본체는 bistro_news.extract
├── add_article.py         # 기사 텍스트 블록 → articles/<id>.json 인테이크
├── models.example.json    # 백엔드/모델/자격증명(env) 설정 템플릿 → models.json 으로 복사(gitignore)
├── extract_from_xlsx.py   # (초기) 간이 비교 평가 시트 → predictions (bistro_news.io 파서)
├── predictions/           # 기사 × 설정별 모델 출력 (core_event 정규화 + 원문)
├── gold/gold.json         # 수작업 정답. 스펙 규칙으로 도출 가능한 판단만.
├── score.py               # 지표 계산 + report.md 생성
└── report.md              # 자동 생성 결과
```

> 공용 로직(JSON-ish 파서·모델 클라이언트·프롬프트 로더·4-step 파이프라인)은 `src/bistro_news/` 패키지에 있고 eval 스크립트는 이를 import 한다. 설치 없이 실행되도록 각 스크립트가 `src/` 를 sys.path 에 넣는다(정식 사용은 `pip install -e .`).

## 기사 1건 늘리는 절차

1. `eval/articles/<article_id>.json` 추가 (본문 = 라이선스된 소스에서. 저작권 주의)
2. `python eval/run_extraction.py --article <article_id>` → 4개 설정 출력 생성
3. `eval/gold/gold.json` 에 `<article_id>` 정답 추가 (없으면 gold 기준 지표는 미채점, 자동 지표만)
4. `python eval/score.py`

## 비교 대상

| config_id | 모델 | 프롬프트 | 역할 |
|---|---|---|---|
| `ref_claude4step` | **Claude Opus** | 신규 4-step | **reference (기준)** |
| `new4step_hcx32b` | HCX-32B | 신규 4-step | **검증 대상** |
| `legacy_claude_sonnet46` | Claude Sonnet 4.6 | 기존 단일 | (과거 데이터·곁가지) |
| `legacy_hcx32b_think` | HCX-32B (Think) | 기존 단일 | (과거·탈락) |
| `legacy_hcx007` | HCX-007 | 기존 단일 | (과거·탈락) |

> 현재 `ref_claude4step` 은 이 세션의 **Opus 4.8 이 수동 생성한 부트스트랩**(자가생성 → silver). 정식화 시 독립 API Opus 호출로 교체. legacy 행은 `간이 비교 평가` 시트에서 인제스트된 과거 데이터로, 신규 4-step의 Step A(core)만 있어 평가는 **Core Event 추출**(기사당 1개 + is_factual 게이트)에 집중한다.

## 지표 (사용자 결정: 기준점 불요 + gold 둘 다)

**[A] 자동 객관 지표 (정답 불요)** — `parse_ok`, `core_extracted`(core 1개), `event_type_valid`(enum 준수), `w5h1_completeness`, `no_leak`(`<think>`/영어 지시문 누출), `no_kr_enum`(한글 enum 값 위반)

**[B] gold 기준 (수작업 2건)** — `core_topic_correct`(올바른 사건을 core로), `is_factual_correct`(비사실 사건을 사실 core로 오선택하지 않음)

**종합** — `core_quality_pass` = 위 핵심 항목 전부 통과. `claude_agreement` = Claude 설정과 같은 정오 버킷인가.

## 현재 결과 요약 (n=2)

| 설정 | 종합 합격 |
|---|---|
| `ref_claude4step` (Claude Opus, 기준) | 2/2 🟢 |
| **`new4step_hcx32b`** | **2/2 🟢** |
| `legacy_claude_sonnet46` (과거) | 2/2 🟢 |
| `legacy_hcx32b_think` (과거) | 0/2 🔴 |
| `legacy_hcx007` (과거) | 0/2 🔴 |

신규 4-step이 동일 HCX-32B의 legacy 실패(통행료 오선택·core 누락·`<think>`/영어 누출·한글 enum)를 교정해 **이 2건에서는 Claude Opus reference 와 동률**. 단 n=2 + reference 가 Opus 부트스트랩(자가생성) — 일반화·정식 결론 불가.

## ⚠️ 한계 & 다음 단계

- **n=2.** 통계적 결론 아님. 기사 수를 늘려야 한다(목표 수십~수백 건).
- **gold가 silver에 가깝다.** 정답은 스펙 규칙으로 도출했고 사람 검수 1패스 권장.
- **Core 중심.** Background/Consequence·인덱스화 품질은 별도 평가 필요(신규 4-step의 B/C/D 출력 확보 후).
- 새 기사 추가 절차: 원본에 행 추가 → `extract_from_xlsx.py` 재실행 → `gold/gold.json` 에 해당 article 항목 추가 → `score.py`.
