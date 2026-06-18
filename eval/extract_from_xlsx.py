#!/usr/bin/env python3
"""
xlsx `간이 비교 평가` 시트 → eval/predictions/*.json 일회성 인제스트.

원본 xlsx는 .gitignore 대상(설계 참고용). 여기서 추출한 predictions/*.json만
버전관리해 xlsx 없이도 score.py 재현이 가능하도록 한다.

시트 구조 (수기 파악):
  - 행 블록: 기사1 호르무즈 = R2~15, 기사2 범정부 TF = R16~29 (C1 메타정보가 블록 시작)
  - C2 = 요소 마커(core / backgrounds / consequences / entities / extraction_quality)
  - 설정별 컬럼:
      C3 = 기존 단일프롬프트 / HCX-007
      C4 = 기존 단일프롬프트 / HCX-32B (Think)
      C5 = 기존 단일프롬프트 / Claude Sonnet 4.6
      C6 = 신규 4-step      / HCX-32B
  - 신규(C6)는 이 시트에 Step A(core)만 있고 B/C/D는 없음 → core 중심 비교.

셀은 완전한 JSON이 아닌 단편(중괄호 없는 내부 필드, 표 형태 등)이 섞여 있어
관대한 파서로 core_event를 정규화한다. 파싱 실패/누출 자체가 품질 지표가 된다.

사용: python eval/extract_from_xlsx.py [xlsx경로]
"""
import json
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))  # 패키지 import
from bistro_news.io import parse_core  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_XLSX = REPO / "docs" / "spec" / "뉴스 인과관계 분석.xlsx"
OUT_DIR = Path(__file__).resolve().parent / "predictions"

# (시작행, 끝행, article_id, 제목요약)
ARTICLES = [
    (2, 15, "hormuz_toll_20260408", "호르무즈 통행료 체계 / 美·이란 휴전"),
    (16, 29, "transit_tf_20260408", "출퇴근 혼잡완화 범정부 TF 발족"),
]
# 컬럼 → 설정 메타
CONFIGS = {
    3: {"config_id": "legacy_hcx007", "family": "legacy_single", "model": "HCX-007"},
    4: {"config_id": "legacy_hcx32b_think", "family": "legacy_single", "model": "HCX-32B(Think)"},
    5: {"config_id": "legacy_claude_sonnet46", "family": "legacy_single", "model": "Claude Sonnet 4.6"},
    6: {"config_id": "new4step_hcx32b", "family": "new_4step", "model": "HCX-32B"},
}
def main():
    xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLSX
    if not xlsx.exists():
        sys.exit(f"xlsx not found: {xlsx}\n원본을 docs/ 에 두거나 경로를 인자로 넘기세요.")
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    ws = wb["간이 비교 평가"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    def cell(r, c):
        v = ws.cell(r, c).value
        return None if v is None or str(v).strip() == "" else str(v)

    written = 0
    for start, end, article_id, title in ARTICLES:
        # 블록 안 요소 마커 행 찾기
        marker_rows = {}
        for r in range(start, end + 1):
            m = cell(r, 2)
            if m:
                marker_rows[m.strip()] = r
        core_row = marker_rows.get("core", start)

        for col, meta in CONFIGS.items():
            raw_core = cell(core_row, col)
            core, status = parse_core(raw_core)
            # 설정의 기사 블록 전체 원문 (누출/한글enum 텍스트 스캔용)
            block = "\n".join(filter(None, (cell(r, col) for r in range(start, end + 1))))
            rec = {
                "article_id": article_id,
                "title": title,
                "config_id": meta["config_id"],
                "family": meta["family"],
                "model": meta["model"],
                "core_event": core,
                "parse_status": status,
                "raw_core": raw_core,
                "raw_block": block,
            }
            out = OUT_DIR / f"{article_id}__{meta['config_id']}.json"
            out.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            written += 1
            print(f"  {out.name:48s} core={'∅' if core is None else '●'} [{status}]")
    print(f"\n{written} predictions → {OUT_DIR}")


if __name__ == "__main__":
    main()
