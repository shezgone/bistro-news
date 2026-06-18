# ingest — 1. 뉴스 수집 + 중복제거

기사 수집 → SHA256 해시로 완전 동일 제거 → BGE-M3 임베딩 유사 클러스터링(`cluster_uuid`).

구현체: `BAAI/bge-m3` (sentence-transformers / FlagEmbedding). 본문은 copyright-by-design상 해시·임베딩 후 폐기.

> 미구현 스텁. 이 단계 코드는 여기에 둔다.
