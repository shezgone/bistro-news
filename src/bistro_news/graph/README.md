# graph — 4. 인과 전파 그래프 + 3단계 엣지 필터

노드=이벤트(5W1H+event_type), 엣지=방향성 가중 인과. intra-article(추출이 직접 생성) + inter-article(클러스터 매칭, REALIZED_AS).

엣지 검증 3단계: Phase1 시간 방향성 게이트 → Phase2 가중치(선행성×유사도×보도빈도) → Phase3 LLM CRITIC + PCMCI 이중검증. 구현체: networkx.

> 미구현 스텁. 이 단계 코드는 여기에 둔다.
