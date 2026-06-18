#!/usr/bin/env python3
"""
기사 + prompts/step_*.md → 모델 호출 → predictions/*.json (score.py 입력).

추출 본체는 패키지(`bistro_news.extract`)에 있고, 여기는 평가용 CLI 래퍼다.
기사 수를 늘리려면:
  1) eval/articles/<id>.json 추가  ({article_id,title,write_time,publisher,body})
  2) python eval/run_extraction.py
  3) python eval/score.py
  4) eval/gold/gold.json 에 해당 기사 정답 추가

백엔드/모델/자격증명 = eval/models.json (models.example.json 복사). 시크릿은 env 로만.
자격증명 없이도 `--dry-run` 으로 프롬프트 렌더링 검증 가능.

사용:
  python eval/run_extraction.py --dry-run
  python eval/run_extraction.py
  python eval/run_extraction.py --config new4step_hcx32b --article hormuz_toll_20260408
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))  # editable install 없이도 패키지 import

from bistro_news.extract import run_legacy, run_new4step  # noqa: E402

ARTICLES_DIR = HERE / "articles"
PRED_DIR = HERE / "predictions"
MODELS_CFG = HERE / "models.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", help="특정 config_id 만")
    ap.add_argument("--article", help="특정 article_id 만")
    ap.add_argument("--dry-run", action="store_true", help="호출 없이 렌더링만")
    args = ap.parse_args()

    cfg_path = MODELS_CFG if MODELS_CFG.exists() else (HERE / "models.example.json")
    if cfg_path.name == "models.example.json" and not args.dry_run:
        print("⚠️ eval/models.json 없음 → models.example.json 사용. 실제 호출엔 models.json 작성 필요.", file=sys.stderr)
    configs = json.loads(cfg_path.read_text(encoding="utf-8"))["configs"]
    if args.config:
        configs = {args.config: configs[args.config]}

    arts = sorted(ARTICLES_DIR.glob("*.json"))
    if args.article:
        arts = [p for p in arts if p.stem == args.article]
    if not arts:
        raise SystemExit(f"기사 없음: {ARTICLES_DIR} (article_id={args.article})")

    PRED_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    for ap_ in arts:
        art = json.loads(ap_.read_text(encoding="utf-8"))
        for cid, cfg in configs.items():
            runner = run_new4step if cfg["family"] == "new_4step" else run_legacy
            try:
                core, status, raw = runner(cfg, art, args.dry_run)
            except Exception as e:
                print(f"  ✗ {art['article_id']} × {cid}: {type(e).__name__}: {e}", file=sys.stderr)
                continue
            if args.dry_run:
                print(f"  (dry) {art['article_id']} × {cid}")
                continue
            rec = {"article_id": art["article_id"], "title": art["title"],
                   "config_id": cid, "family": cfg["family"], "model": cfg.get("model_label", cfg["model"]),
                   "core_event": core, "parse_status": status, "raw_core": raw[:4000], "raw_block": raw}
            out = PRED_DIR / f"{art['article_id']}__{cid}.json"
            out.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  {out.name:52s} core={'∅' if core is None else '●'} [{status}]")
            n += 1
    if not args.dry_run:
        print(f"\n{n} predictions → {PRED_DIR}\n다음: python eval/score.py")


if __name__ == "__main__":
    main()
