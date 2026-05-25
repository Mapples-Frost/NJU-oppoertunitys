# NJU Opportunity Radar

NJU Opportunity Radar 是一个面向南京大学学生的个人机会情报系统。它每天从公开网页、RSS/API、微信公众号公开文章、邮件/手动/Webhook 转发入口中抓取与 AI、机器人、自动化、算法、科研训练、讲座、竞赛、企业活动相关的信息，完成去重、分类、打分、截止时间识别、SQLite 入库，并生成邮件日报。

## Quick Start

新手配置请先看：[docs/操作手册.md](docs/操作手册.md)。

```bash
python -m pip install -r requirements.txt
python -m radar.main --config config --dry-run
```

真实运行并写入数据库：

```bash
python -m radar.main --config config
```

发送邮件需要配置环境变量或 GitHub Secrets：

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=your-account@example.com
SMTP_PASS=your-mail-authorization-code
MAIL_FROM=your-account@example.com
MAIL_TO=receiver@example.com
python -m radar.main --config config --send-email
```

## Configuration

- `config/sources.yml`：信息源配置。V1 已接入 30+ 个启用源，新增网站通常只改这个文件。
- `config/wechat_watchlist.yml`：微信公众号重点关注列表和标签。
- `config/keywords.yml`：正向关键词和排除词。
- `config/scoring.yml`：打分权重和邮件阈值。
- `config/profile.yml`：个人关注画像，控制哪些机会更值得看。
- `config/quality.yml`：质量门、可行动判定、Top 15 邮件规则。
- `config/email.yml`：非敏感邮件展示配置。
- `inbox/manual.md`：手动转发入口。
- `inbox/feedback.yml`：用户反馈入口，可拒绝噪音、提升偏好来源。
- `inbox/wechat_articles.md`：微信公众号公开文章链接池。
- `inbox/webhook_inbox.jsonl`：Webhook/快捷指令转发入口。

V2 source packs：

| Pack | 用途 |
|---|---|
| `wechat_pack` | 微信公众号公开文章、邮件转发、Webhook 转发、手动入口 |
| `competition_pack` | AI/算法/机器人/创新创业/企业赛事 |
| `research_pack` | 学会、会议 CFP、科研项目、学术活动 |
| `nju_pack` | 南大校内公开信息源 |

## Runtime Files

- `data/opportunities.sqlite`：历史机会库，首次非 dry-run 自动创建。
- `logs/latest_run.json`：最近一次运行摘要。
- `logs/latest_email.html` / `logs/latest_email.txt`：最近一次渲染出的日报。
- `logs/latest_history_email.html` / `logs/latest_history_email.txt`：最近一次历史汇总邮件。
- `logs/latest_quality_report.json`：最近一次质量过滤统计。
- `logs/latest_rejected_items.json`：最近一次被质量门过滤的条目。
- `logs/source_quality.json`：各 source 的质量表现。

## GitHub Actions

`.github/workflows/daily.yml` 每天 08:00 Asia/Shanghai 运行一次。GitHub Actions 的 cron 使用 UTC，因此 workflow 中写为 `0 0 * * *`。

手动运行 workflow 时可以选择 `mode=history`，系统会从 `data/opportunities.sqlite` 读取历史库并发送一封历史机会汇总邮件。`history_limit=0` 表示发送全部历史机会；也可以填一个数字只发送分数最高的前 N 条。

V3 开始每日邮件采用质量优先策略：正文展示本次抓取中通过质量门的 Top 15，即使它们已经在历史库中也会进入当天日报；系统异常和低质候选进入日志。手动运行 workflow 时选择 `mode=quality` 只生成质量报告，不会发送邮件。

邮件发送需要在 GitHub 仓库 Secrets 中配置：

```text
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASS
MAIL_FROM
MAIL_TO
```

如果 Secrets 不完整，Action 会直接失败并提示缺少邮件配置，避免出现绿色成功但没有发送邮件的情况。

可选 IMAP 转发入口使用这些 Secrets。未配置时会自动跳过，不会导致运行失败：

```text
IMAP_HOST
IMAP_PORT
IMAP_USER
IMAP_PASS
```

可选 LLM 复核使用这些 Secrets。未配置时自动跳过，规则流程仍正常运行：

```text
LLM_API_KEY
LLM_MODEL
LLM_BASE_URL
```

## Safety Boundary

系统只抓公开网页、公开 RSS/API、微信公众号公开文章链接和用户本人授权/主动转发的信息；不绕登录、验证码、反爬，不抓取需要校内账号登录的系统，不高频请求。
