# NJU Opportunity Radar

NJU Opportunity Radar 是一个面向南京大学学生的个人机会情报系统。它每天从公开网页、RSS/API 和手动入口中抓取与 AI、机器人、自动化、算法、科研训练、讲座、竞赛、企业活动相关的信息，完成去重、分类、打分、截止时间识别、SQLite 入库，并生成邮件日报。

## Quick Start

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
- `config/keywords.yml`：正向关键词和排除词。
- `config/scoring.yml`：打分权重和邮件阈值。
- `config/email.yml`：非敏感邮件展示配置。
- `inbox/manual.md`：手动转发入口。

## Runtime Files

- `data/opportunities.sqlite`：历史机会库，首次非 dry-run 自动创建。
- `logs/latest_run.json`：最近一次运行摘要。
- `logs/latest_email.html` / `logs/latest_email.txt`：最近一次渲染出的日报。

## GitHub Actions

`.github/workflows/daily.yml` 每天 08:00 Asia/Shanghai 运行一次。GitHub Actions 的 cron 使用 UTC，因此 workflow 中写为 `0 0 * * *`。

需要在 GitHub 仓库 Secrets 中配置：

```text
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASS
MAIL_FROM
MAIL_TO
```

如果 Secrets 不完整，Action 仍会运行抓取和日报渲染，只是不发送邮件。

## Safety Boundary

V1 只抓公开网页、公开 RSS/API 和用户手动提供的信息；不绕登录、验证码、反爬，不抓取需要校内账号登录的系统，不高频请求。
