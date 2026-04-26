# economist-reader

每小时自动抓取 The Economist 文章 → Gemma 3 27B 翻译 → 生成中英对照 PDF → 上传 Cloudflare R2 → 浏览器访问 [economist.897654321.space](https://economist.897654321.space)

## 本地跑

```bash
uv sync --extra dev
cp .env.example .env  # 填好 GEMINI_API_KEY
uv run python cli.py --limit 1   # 只抓一篇试试
uv run python cli.py             # 抓首页所有未处理文章
```

## 架构

```
首页抓取 → URL diff → 单文章抓取 → Gemma 3 27B 翻译 → ReportLab PDF → R2 上传
```

| 模块 | 职责 |
|------|------|
| `src/econ/scraper.py` | bs4 + UA 伪装抓 economist.com |
| `src/econ/ai.py` | Gemma 3 27B 调用（带 JSON 容错） |
| `src/econ/pdf.py` | ReportLab 生成中英对照 PDF |
| `src/econ/r2.py` | S3-compatible API 上传到 Cloudflare R2 |
| `src/econ/state.py` | 通过远程 API 查已处理 URL（无状态） |
| `src/econ/pipeline.py` | 主流水线编排 |
| `cli.py` | argparse 入口 |

## CI/CD

GitHub Actions cron 每小时跑（`.github/workflows/hourly.yml`）。无新文章时几乎零开销（只抓一次首页 HTML）。
