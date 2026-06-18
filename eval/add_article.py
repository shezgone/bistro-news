#!/usr/bin/env python3
"""
기사 텍스트 블록 → eval/articles/<article_id>.json 인테이크.

기사 확대용. 기획팀 자료(events.pptx·xlsx)나 라이선스 소스의 기사를 아래 형식 텍스트로
저장하면 평가 입력 JSON 으로 변환한다. article_id = 입력 파일명(확장자 제외).

입력 텍스트 형식 (━ 테두리 있어도 됨):
    제목: <기사 제목>
    작성일시: <YYYY.MM.DD. ...>
    언론사: <언론사>

    <본문 ...>

사용:
    python eval/add_article.py path/to/<article_id>.txt [더 많은 파일...]
    python eval/add_article.py raw_articles/        # 디렉터리 내 *.txt 일괄
    cat article.txt | python eval/add_article.py --id my_article_20260618 -

변환 후:
    python eval/run_extraction.py --article <article_id>   # 모델 호출(자격증명 필요)
    # 또는 Opus 부트스트랩 reference 를 수동 생성
    python eval/score.py
"""
import argparse
import json
import re
import sys
from pathlib import Path

ARTICLES_DIR = Path(__file__).resolve().parent / "articles"


def parse_block(text):
    """메타정보 블록 + 본문 → dict(title, write_time, publisher, body)."""
    def grab(label):
        m = re.search(rf"{label}\s*[:：]\s*(.+)", text)
        return m.group(1).strip() if m else None

    title = grab("제목")
    write_time = grab("작성일시") or grab("작성일") or grab("일시")
    publisher = grab("언론사") or grab("출처")

    # 본문: '기사' 마커 이후, 없으면 언론사 줄 이후
    if "기사" in text:
        body = text.split("기사", 1)[1]
    elif publisher:
        body = text.split(publisher, 1)[1]
    else:
        body = text
    body = re.sub(r"^[━─=\s]+", "", body)
    body = re.sub(r"[━─=\s]+$", "", body).strip()
    return {"title": title, "write_time": write_time, "publisher": publisher, "body": body}


def write_article(article_id, parsed):
    missing = [k for k in ("title", "write_time", "publisher", "body") if not parsed.get(k)]
    rec = {"article_id": article_id, **parsed}
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    out = ARTICLES_DIR / f"{article_id}.json"
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    warn = f"  ⚠️ 누락 필드: {missing}" if missing else ""
    print(f"  {out.name:40s} body_chars={len(parsed['body'])}{warn}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="텍스트 파일/디렉터리, 또는 '-' (stdin)")
    ap.add_argument("--id", help="stdin 사용 시 article_id")
    args = ap.parse_args()

    n = 0
    for p in args.paths:
        if p == "-":
            if not args.id:
                sys.exit("stdin 입력엔 --id 필요")
            write_article(args.id, parse_block(sys.stdin.read()))
            n += 1
            continue
        path = Path(p)
        files = sorted(path.glob("*.txt")) if path.is_dir() else [path]
        for f in files:
            write_article(f.stem, parse_block(f.read_text(encoding="utf-8")))
            n += 1
    print(f"\n{n} articles → {ARTICLES_DIR}")


if __name__ == "__main__":
    main()
