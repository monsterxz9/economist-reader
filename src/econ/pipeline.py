import sys
import tempfile
from pathlib import Path

from econ import ai, pdf, r2, scraper, state


def process_one(url: str, dry_run: bool = False, no_upload: bool = False, output_dir: Path | None = None) -> dict:
    """Returns a status dict: {'url', 'status', 'reason'?, 'key'?}."""
    print(f"\n📰 {url}")

    try:
        article = scraper.fetch_article(url)
    except Exception as e:
        return {"url": url, "status": "scrape_failed", "reason": str(e)}

    date = article["date"]
    title = article["title"]
    print(f"   标题: {title}")
    print(f"   日期: {date}, 正文 {len(article['body'])} 字符")

    if not date:
        return {"url": url, "status": "no_date"}

    if state.is_already_uploaded(date, url, title):
        return {"url": url, "status": "already_uploaded", "key": f"{date}/pdf/{state.pdf_filename(url, title)}"}

    if dry_run:
        return {"url": url, "status": "dry_run_ok"}

    print("   → Gemma 3 27B 翻译中...")
    try:
        data = ai.analyze(article["title"], article["body"])
    except Exception as e:
        return {"url": url, "status": "ai_failed", "reason": str(e)}

    title_en = data.get("title_en") or title
    filename = state.pdf_filename(url, title_en)
    print(f"   → 生成 PDF: {filename}")

    if no_upload:
        local_dir = (output_dir or Path("output")) / date
        local_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = local_dir / filename
        try:
            pdf.generate(data, pdf_path)
        except Exception as e:
            return {"url": url, "status": "pdf_failed", "reason": str(e)}
        return {"url": url, "status": "saved_local", "path": str(pdf_path)}

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / filename
        try:
            pdf.generate(data, pdf_path)
        except Exception as e:
            return {"url": url, "status": "pdf_failed", "reason": str(e)}

        key = f"{date}/pdf/{filename}"
        print(f"   → 上传 R2: {key}")
        try:
            r2.upload(pdf_path, key)
        except Exception as e:
            return {"url": url, "status": "upload_failed", "reason": str(e)}

    return {"url": url, "status": "uploaded", "key": key}


def run(
    limit: int = 20,
    dry_run: bool = False,
    no_upload: bool = False,
    urls: list[str] | None = None,
) -> int:
    """Returns exit code (0 = ok, even if some articles failed)."""
    if urls is None:
        print(f"📋 抓取首页文章列表 (limit={limit})...")
        urls = scraper.list_homepage_articles(limit=limit)
        print(f"   找到 {len(urls)} 篇候选")

    results = [process_one(u, dry_run=dry_run, no_upload=no_upload) for u in urls]

    print("\n" + "=" * 60)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    for status, n in sorted(counts.items()):
        print(f"  {status}: {n}")

    failed = [r for r in results if r["status"].endswith("_failed")]
    if failed:
        print("\n❌ 失败详情:")
        for r in failed:
            print(f"  - {r['url']}: {r.get('reason', '')[:200]}", file=sys.stderr)

    return 0
