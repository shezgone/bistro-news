"""BISTRO-News — 뉴스 기반 인과관계 분석 파이프라인.

단계별 서브패키지 (CLAUDE.md 6단계):
  ingest   1. 뉴스 수집 + 중복제거 (SHA256, BGE-M3)
  extract  2. LLM 4-step 이벤트 추출
  cluster  3. 이벤트 클러스터링
  graph    4. 인과 전파 그래프 + 3단계 엣지 필터
  index    5. 인덱스화 (centrality Track A/B)
  validate 6. 역방향 검증 (Granger / PCMCI / lead-lag)

공용: io(JSON-ish 파서), llm(모델 클라이언트 + 프롬프트 로더).
"""

__version__ = "0.1.0"
