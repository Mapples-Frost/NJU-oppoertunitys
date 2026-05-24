# NJU Opportunity Radar：每日机会自动抓取与邮件推送系统方案

> 面向南京大学学生的个人机会情报系统。目标是每天自动发现与 **AI、机器人、自动化、算法、科研训练、讲座、竞赛、企业活动** 相关的信息，并通过邮箱推送结构化日报。

---

## 0. 项目定位

你要做的不是一个简单的“RSS 邮件订阅器”，而是一个长期可运行、可扩展、可维护的 **个人机会雷达系统**。

核心目标：

```text
每天自动发现南大校内 + 校外企业 / 学会 / 竞赛平台中与你相关的机会，
经过抓取、去重、分类、打分、摘要后，推送到你的邮箱。
```

典型机会包括：

- 校内竞赛通知
- 学院讲座 / 学术报告
- 大创 / 科研训练 / 项目招募
- 志愿活动 / 培训课程 / 训练营
- 华为、阿里、腾讯、字节、百度、讯飞等企业赛
- RoboCup、智能车、蓝桥杯、CCF、DataFountain、天池等竞赛
- AI、大模型、多模态、机器人、自动化、控制、视觉、嵌入式相关活动

---

## 1. 总体架构

```text
定时触发：GitHub Actions
        ↓
读取 sources.yml 信息源配置
        ↓
多源抓取：
RSS / RSSHub / 官网列表页 / 官网详情页 / API / 手动转发入口
        ↓
正文抽取与标准化
        ↓
去重：URL 去重 + 标题指纹 + 相似标题合并
        ↓
分类：比赛 / 讲座 / 训练营 / 大创 / 科研项目 / 企业活动 / 实习入口
        ↓
相关性打分：AI、机器人、自动化、算法、企业含金量、截止时间
        ↓
截止时间抽取
        ↓
写入 SQLite 数据库
        ↓
生成每日邮件摘要
        ↓
SMTP 发到邮箱
        ↓
提交数据库状态和运行日志回 GitHub 仓库
```

---

## 2. 技术选型

| 模块 | 推荐方案 |
|---|---|
| 定时运行 | GitHub Actions |
| 主语言 | Python |
| RSS 抓取 | `feedparser` |
| 网页抓取 | `requests` + `BeautifulSoup` |
| 正文抽取 | `trafilatura`，失败时 fallback 到 BeautifulSoup |
| 动态网页 | Playwright，仅用于少量关键公开页面 |
| 数据库 | SQLite |
| 去重 | URL canonicalize + hash + title similarity |
| 时间抽取 | 正则 + `dateparser` |
| 分类打分 | 规则优先，后续可接 LLM |
| 邮件发送 | Python `smtplib` |
| 状态保存 | SQLite 文件提交回仓库 |
| 配置管理 | YAML |

推荐理由：

- **GitHub Actions**：适合作为第一版运行平台，不需要一开始购买服务器。
- **SQLite**：简单、稳定、可直接提交到仓库保存历史状态。
- **YAML 配置化**：新增网站时尽量只改配置，不改主逻辑。
- **规则优先**：稳定、可解释、低成本；LLM 可以作为增强模块，而不是核心依赖。

---

## 3. 信息源设计

第一版质量的核心不在代码量，而在信息源质量。建议分层接入。

### 3.1 Layer 1：南京大学校内公开信息源

重点关注：

```text
南京大学本科生院
南京大学创新创业学院
南京大学人工智能学院
南京大学计算机学院 / 计算机科学与技术系
南京大学软件学院
南京大学电子科学与工程学院
南京大学现代工程与应用科学学院
南京大学就业创业相关页面
南京大学团委 / 志愿活动 / 第二课堂相关平台
各院系“通知公告”“学术报告”“学生工作”“本科教学”栏目
```

主要抓取：

```text
校内竞赛
大创
讲座
短期课程
科研训练
学术报告
志愿活动
训练营
学院组织的企业合作活动
```

### 3.2 Layer 2：竞赛平台

```text
阿里天池
科大讯飞 AI 开发者大赛
DataFountain
蓝桥杯
中国机器人大赛 / RoboCup 中国赛
全国大学生智能汽车竞赛
CCF CSP / CCSP / C4
Kaggle
百度飞桨 AI Studio
ModelScope / 魔搭社区
启智社区 OpenI
```

### 3.3 Layer 3：企业开发者和大厂赛事

```text
华为开发者联盟
华为软件精英挑战赛
华为云开发者
阿里云开发者
腾讯云开发者
火山引擎 / 字节跳动开发者
百度飞桨
讯飞开放平台
蚂蚁集团技术活动
小米、OPPO、vivo 开发者赛事
```

### 3.4 Layer 4：学会、会议、学术组织

```text
中国自动化学会
中国人工智能学会
中国计算机学会 CCF
中国图象图形学学会 CSIG
IEEE / ACM 相关学生竞赛
机器人、智能系统、控制、视觉方向会议通知
```

### 3.5 Layer 5：手动入口

微信公众号、微信群、QQ群、校内群聊不建议第一版强爬。正确做法是提供一个手动入口：

```text
看到有价值消息
→ 转发 / 粘贴到 inbox/manual.md
→ 系统每天读取 manual.md
→ 一起进入分类、去重、打分、日报
```

这样可以覆盖：

- 公众号转发
- 群聊转发
- 学长学姐推荐
- 老师口头通知
- 朋友发来的比赛链接

---

## 4. 仓库结构

建议仓库名：

```text
nju-opportunity-radar
```

目录结构：

```text
nju-opportunity-radar/
├── .github/
│   └── workflows/
│       └── daily.yml
├── config/
│   ├── sources.yml
│   ├── keywords.yml
│   ├── scoring.yml
│   └── email.yml
├── radar/
│   ├── __init__.py
│   ├── main.py
│   ├── fetchers/
│   │   ├── rss_fetcher.py
│   │   ├── html_list_fetcher.py
│   │   ├── html_detail_fetcher.py
│   │   ├── api_fetcher.py
│   │   └── manual_fetcher.py
│   ├── extractors/
│   │   ├── content_extractor.py
│   │   ├── deadline_extractor.py
│   │   └── metadata_extractor.py
│   ├── classifiers/
│   │   ├── rule_classifier.py
│   │   └── llm_classifier.py
│   ├── rankers/
│   │   └── opportunity_ranker.py
│   ├── storage/
│   │   ├── db.py
│   │   └── migrations.py
│   ├── mailer/
│   │   ├── render_email.py
│   │   └── send_email.py
│   └── utils/
│       ├── url.py
│       ├── text.py
│       ├── hash.py
│       └── logging.py
├── data/
│   └── opportunities.sqlite
├── logs/
│   └── latest_run.json
├── inbox/
│   └── manual.md
├── tests/
│   ├── fixtures/
│   └── test_dedup.py
├── requirements.txt
└── README.md
```

---

## 5. `sources.yml` 设计

`config/sources.yml` 是整个系统最核心的配置文件。所有信息源都应该配置化，不要硬编码进 Python 代码。

示例：

```yaml
sources:
  - id: nju_undergraduate
    name: 南京大学本科生院
    type: html_list
    group: nju
    category_hint: 校内通知
    enabled: true
    base_url: "https://example.com"
    list_url: "https://example.com/news"
    list_selector: ".news-list a"
    title_selector: "a"
    link_selector: "a"
    date_selector: ".date"
    detail_required: true
    detail_content_selector: "article, .content, .main"
    tags:
      - NJU
      - 校内
      - 本科生
    weight: 1.2

  - id: alibaba_tianchi
    name: 阿里天池
    type: rss
    group: competition
    category_hint: AI竞赛
    enabled: true
    feed_url: "这里放 RSS 或 RSSHub 地址"
    tags:
      - AI
      - 算法
      - 企业赛
    weight: 1.3

  - id: datafountain
    name: DataFountain
    type: html_list
    group: competition
    category_hint: 数据竞赛
    enabled: true
    list_url: "这里放比赛列表页"
    list_selector: "这里放比赛卡片选择器"
    detail_required: true
    tags:
      - AI
      - 数据竞赛
    weight: 1.2

  - id: manual_inbox
    name: 手动转发入口
    type: manual
    group: manual
    path: "inbox/manual.md"
    enabled: true
    tags:
      - 手动
      - 群聊
      - 公众号
    weight: 1.0
```

### 5.1 信息源类型

| 类型 | 说明 |
|---|---|
| `rss` | 原生 RSS 或 RSSHub 输出 |
| `html_list` | 普通网页列表页 |
| `api` | JSON API |
| `manual` | 手动入口，如 `inbox/manual.md` |
| `playwright` | 少量必须动态渲染的公开页面 |

---

## 6. 关键词系统

`config/keywords.yml` 不要只有简单 include，还要有权重和排除词。

```yaml
positive:
  high:
    - 机器人
    - RoboCup
    - 智能车
    - 自动化
    - 控制
    - 人工智能
    - AI
    - 大模型
    - 多模态
    - 智能体
    - 视觉
    - 具身智能
    - 强化学习
    - 机器学习
    - 算法
    - 数据挖掘
    - 华为软件精英
    - 天池
    - 讯飞
    - DataFountain
    - CCF

  medium:
    - 竞赛
    - 挑战赛
    - 开发者大赛
    - 创新赛
    - 训练营
    - 夏令营
    - 学术报告
    - 讲座
    - 大创
    - 科研训练
    - 实践项目

  low:
    - 志愿
    - 培训
    - 课程
    - 沙龙
    - 分享会

negative:
  - 纯文体活动
  - 摄影比赛
  - 征文
  - 非技术岗招聘
  - 后勤通知
  - 失物招领
  - 会议室安排
  - 党课
```

---

## 7. 数据库设计

推荐使用 SQLite。第一版至少包含 4 张表。

### 7.1 `opportunities`

```sql
CREATE TABLE opportunities (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT,
    source_id TEXT,
    source_name TEXT,
    source_group TEXT,
    published_at TEXT,
    discovered_at TEXT NOT NULL,
    deadline_at TEXT,
    event_start_at TEXT,
    event_end_at TEXT,
    date_confidence TEXT,
    date_source_text TEXT,
    content TEXT,
    summary TEXT,
    category TEXT,
    tags TEXT,
    score REAL,
    relevance_score REAL,
    organizer_score REAL,
    deadline_score REAL,
    novelty_score REAL,
    status TEXT DEFAULT 'new',
    content_hash TEXT,
    title_hash TEXT,
    url_hash TEXT
);
```

### 7.2 `sources`

```sql
CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    enabled INTEGER,
    last_success_at TEXT,
    last_error_at TEXT,
    last_error TEXT,
    total_found INTEGER DEFAULT 0
);
```

### 7.3 `runs`

```sql
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    started_at TEXT,
    finished_at TEXT,
    status TEXT,
    total_sources INTEGER,
    successful_sources INTEGER,
    failed_sources INTEGER,
    total_items INTEGER,
    new_items INTEGER,
    emailed_items INTEGER
);
```

### 7.4 `dedup_index`

```sql
CREATE TABLE dedup_index (
    key TEXT PRIMARY KEY,
    opportunity_id TEXT,
    key_type TEXT,
    created_at TEXT
);
```

---

## 8. 抓取策略

### 8.1 抓取优先级

```text
RSS 原生源
→ RSSHub 源
→ HTML 列表页
→ HTML 详情页
→ Playwright 动态页面
```

不要一开始就用 Playwright 跑所有网站。Playwright 只用于少数关键、公开、静态抓不到内容的页面。

### 8.2 RSS / RSSHub 抓取

RSS 是最优先的来源，原因是：

- 稳定
- 对目标网站压力小
- 内容结构清楚
- 易于增量更新

### 8.3 HTML 列表页抓取

对每个 HTML 源配置以下字段：

```text
list_selector
title_selector
link_selector
date_selector
detail_content_selector
```

流程：

```text
抓列表页
→ 解析标题、链接、发布时间
→ 进入详情页
→ 抽取正文
→ 标准化字段
```

正文抽取顺序：

```text
trafilatura
→ detail_content_selector
→ BeautifulSoup 简单抽取
→ 保留标题和摘要
```

### 8.4 API 源

有些平台页面背后是 JSON API。第一版可以支持 `api` 类型：

```yaml
type: api
method: GET
url: "..."
items_path: "data.list"
title_path: "title"
link_path: "url"
date_path: "created_at"
```

### 8.5 手动入口

`inbox/manual.md` 格式示例：

```markdown
## 华为某某挑战赛
链接：https://example.com
来源：微信群转发
内容：这是一个面向 AI 工程和算法方向的挑战赛……
截止：2026-06-15
```

系统每天读取 `manual.md`，并将其作为普通机会进入后续流程。

---

## 9. 去重策略

只靠 URL 去重不够，因为同一个机会可能被多个网站转载。

### 9.1 URL 规范化

处理：

```text
去掉 utm_source、utm_campaign 等追踪参数
统一 http / https
去掉末尾 /
处理重定向后的最终 URL
```

### 9.2 标题 Hash

标题清洗规则：

```text
去空格
去日期
去“关于举办”“通知”“报名开启”等模板词
统一大小写
```

然后计算 hash。

### 9.3 标题相似度

例如：

```text
“关于举办第十二届华为软件精英挑战赛的通知”
“第十二届华为软件精英挑战赛报名启动”
```

这两条应该合并。

建议使用：

```text
rapidfuzz token_set_ratio > 88
```

命中后，保留：

```text
来源更多
正文更完整
截止时间更明确
分数更高
```

的那一条作为主记录。

---

## 10. 分类体系

最终邮件不应该是一堆无序链接，而应该自动归类。

建议分类：

```text
1. 高优先级机会
2. 截止临近
3. AI / 算法竞赛
4. 机器人 / 自动化 / 智能车
5. 企业开发者赛事
6. 校内讲座 / 学术报告
7. 大创 / 科研训练 / 项目招募
8. 志愿 / 低优先级活动
9. 系统异常：哪些信息源抓取失败
```

分类输入：

```text
标题
正文
source tags
URL
主办方
关键词命中
```

第一版建议规则优先，LLM 辅助。

---

## 11. 打分系统

建议总分 100。

```text
总分 =
方向相关性 40
+ 主办方含金量 20
+ 产出价值 15
+ 截止时间紧迫度 10
+ 来源可信度 10
+ 新鲜度 5
```

### 11.1 方向相关性

| 内容 | 分数 |
|---|---:|
| 机器人 / 自动化 / AI / 大模型 / 算法强相关 | 35–40 |
| 计算机、数据、工程相关 | 20–34 |
| 泛科技、创新创业 | 10–19 |
| 弱相关 | 0–9 |

### 11.2 主办方含金量

| 主办方 | 分数 |
|---|---:|
| 华为、阿里、腾讯、字节、百度、讯飞、CCF、中国自动化学会、国家级竞赛 | 16–20 |
| 南大院系、重点实验室、知名高校 | 12–15 |
| 普通社团、普通讲座 | 5–11 |
| 来源不明 | 0–4 |

### 11.3 产出价值

| 产出 | 分数 |
|---|---:|
| 奖项 / 项目作品 / 代码 / 论文 / 实习入口 | 12–15 |
| 证书 / 训练营 / 可写简历 | 8–11 |
| 只是听讲座 | 3–7 |
| 无明显产出 | 0–2 |

### 11.4 邮件推送阈值

```text
score >= 80：高优先级，邮件顶部展示
65 <= score < 80：正常展示
45 <= score < 65：放入“可选机会”
score < 45：默认不进邮件，只入库
```

---

## 12. 截止时间抽取

截止时间识别是质量关键点。

系统需要从标题和正文中提取：

```text
报名截止
提交截止
初赛时间
决赛时间
讲座时间
活动时间
```

中文时间格式要覆盖：

```text
2026年6月15日
6月15日
6月15日24:00
即日起至6月15日
截止至2026年6月15日
报名时间：5月20日-6月10日
```

处理规则：

- 如果没有年份，默认按当前年份。
- 如果解析出的日期已经过去，尝试下一年，但标注 `date_confidence=low`。
- 邮件中对日期不确定的机会明确提示“需要人工确认”。

数据库中保留：

```text
deadline_at
event_start_at
event_end_at
date_confidence
date_source_text
```

邮件提醒：

```text
还有 3 天截止
还有 7 天截止
日期不确定，需要人工确认
```

---

## 13. 每日邮件格式

邮件标题示例：

```text
[NJU Opportunity Radar] 2026-05-24：发现 12 个新机会，3 个高优先级
```

邮件正文示例：

```text
今天新增机会：12 个
高优先级：3 个
截止 7 天内：2 个
抓取失败源：1 个

一、高优先级

1. 华为软件精英挑战赛
分数：91
类型：企业赛 / 算法工程
方向：AI、算法、工程实现
截止：2026-06-10，剩余 17 天
来源：华为开发者
建议：重点关注，尽快找队友
链接：https://example.com

2. RoboCup 中国赛相关通知
分数：88
类型：机器人竞赛
方向：机器人、视觉、控制
截止：未识别
来源：中国自动化学会
建议：问学院竞赛队 / 实验室是否组队
链接：https://example.com

二、截止临近

1. 南大某某大创报名
分数：76
截止：2026-05-27，剩余 3 天
建议：今天确认是否报名

三、AI / 算法竞赛
...

四、校内讲座
...

五、系统状态

成功抓取：28 / 30 个源
失败源：
- xxx：HTTP 403
- yyy：页面结构变化，未识别列表
```

邮件设计原则：

```text
少废话
可行动
有优先级
告诉你下一步该干什么
```

---

## 14. GitHub Actions 配置

`.github/workflows/daily.yml`：

```yaml
name: Daily Opportunity Radar

on:
  schedule:
    - cron: "0 8 * * *"
      timezone: "Asia/Shanghai"
  workflow_dispatch:

concurrency:
  group: opportunity-radar
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  run:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run radar
        env:
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
          MAIL_FROM: ${{ secrets.MAIL_FROM }}
          MAIL_TO: ${{ secrets.MAIL_TO }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
        run: |
          python -m radar.main --config config --send-email

      - name: Commit database and logs
        run: |
          git config user.name "opportunity-radar-bot"
          git config user.email "opportunity-radar-bot@users.noreply.github.com"
          git add data/ logs/
          git commit -m "daily opportunity radar update" || echo "No changes to commit"
          git push
```

> 注意：GitHub Actions 的定时任务可能受到平台调度影响，不应依赖精确到分钟的执行时间。日报场景可以接受一定延迟。

---

## 15. GitHub Secrets

敏感信息不要写进代码，也不要写进配置文件。应放到 GitHub Secrets。

建议配置：

```text
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASS
MAIL_FROM
MAIL_TO
LLM_API_KEY
```

常见 SMTP 示例：

```text
QQ 邮箱：smtp.qq.com，端口 465 或 587
163 邮箱：smtp.163.com
Gmail：smtp.gmail.com
Outlook：smtp.office365.com
```

实际使用时通常需要邮箱“授权码”，不是登录密码。

---

## 16. `requirements.txt`

基础版本：

```text
requests
beautifulsoup4
lxml
feedparser
trafilatura
PyYAML
python-dateutil
dateparser
rapidfuzz
jinja2
markdown
```

如果使用动态网页：

```text
playwright
```

Playwright 安装后还需要：

```bash
python -m playwright install chromium
```

---

## 17. LLM 模块设计

第一版可以加 LLM，但不要让 LLM 负责所有事情。

正确方式：

```text
规则先筛一遍
→ 只把候选机会交给 LLM
→ LLM 输出 JSON
→ 系统校验 JSON
→ 校验失败则退回规则结果
```

LLM 适合负责：

```text
摘要
分类
推荐理由
判断是否和你的方向相关
判断是否值得重点关注
```

LLM 不应该负责：

```text
去重主逻辑
数据库主键
是否发送邮件
截止时间的唯一来源
```

LLM 输出格式示例：

```json
{
  "is_opportunity": true,
  "category": "AI竞赛",
  "relevance": 0.92,
  "summary": "这是一个面向大模型应用开发的企业赛事，适合 AI 工程方向学生参与。",
  "recommended_action": "建议查看赛题并寻找队友。",
  "risk": "截止时间未在正文中明确出现。"
}
```

---

## 18. 质量保障

### 18.1 信息源健康状态

每个源都记录：

```text
last_success_at
last_error_at
error_message
items_found
new_items_found
```

如果某个源连续 3 天失败，邮件里提醒。

### 18.2 运行日志

`logs/latest_run.json` 示例：

```json
{
  "started_at": "2026-05-24T08:00:00+08:00",
  "finished_at": "2026-05-24T08:02:31+08:00",
  "total_sources": 30,
  "successful_sources": 28,
  "failed_sources": 2,
  "total_items": 143,
  "new_items": 12,
  "emailed_items": 9
}
```

### 18.3 Dry Run

支持：

```bash
python -m radar.main --dry-run
```

效果：

```text
只抓取
只分类
打印结果
不发邮件
不写数据库
```

### 18.4 单元测试

至少测试：

```text
URL 去重
标题相似度
中文日期解析
打分逻辑
邮件渲染
source 配置合法性
```

---

## 19. 安全和合规边界

第一版只做：

```text
公开网页
公开 RSS
公开 API
你自己手动提供的信息
```

第一版不做：

```text
绕登录
绕验证码
爬微信群
批量爬微信公众号历史文章
抓取需要校内账号登录的系统
高频请求
绕 robots / 反爬
```

这不是保守，而是为了让系统稳定、长期可用。

你的目标是“不错过机会”，不是挑战平台风控。

---

## 20. V1 交付标准

第一版完成时，应达到以下标准：

```text
1. 至少接入 30 个信息源
2. 每天自动运行一次
3. 邮箱收到结构化日报
4. 有 SQLite 历史库
5. 支持去重
6. 支持截止时间识别
7. 支持分类和打分
8. 支持抓取失败告警
9. 支持手动入口
10. 新增一个网站不需要改主逻辑，只改 sources.yml
```

---

## 21. 推荐实施顺序

虽然你希望第一版全面，但仍建议按模块推进，避免系统一开始就不可调试。

### Phase 1：基础骨架

```text
仓库结构
配置读取
SQLite 初始化
日志系统
GitHub Actions 定时运行
SMTP 邮件发送
```

### Phase 2：抓取能力

```text
RSS 抓取
HTML 列表页抓取
详情页正文抽取
手动入口解析
```

### Phase 3：机会理解

```text
关键词过滤
分类
打分
中文日期抽取
去重
```

### Phase 4：邮件日报

```text
高优先级区
截止临近区
分类展示区
系统异常区
HTML 邮件模板
```

### Phase 5：增强能力

```text
LLM 摘要
LLM 推荐理由
Playwright 支持
更多源接入
健康状态监控
```

---

## 22. 最终推荐方案

第一版推荐组合：

```text
GitHub Actions
+ Python
+ RSSHub / feedparser
+ requests / BeautifulSoup / trafilatura
+ SQLite
+ YAML 配置
+ 规则分类打分
+ 可选 LLM 摘要
+ smtplib 邮件推送
```

不要做成：

```text
一个 Python 文件
十几个硬编码 URL
print 出结果
每天靠自己点运行
```

这个项目可以叫：

```text
NJU Opportunity Radar
```

它不只是解决焦虑，也可以成为一个很像样的 AI 工程项目。简历上可以写成：

```text
构建面向高校学生的机会发现与推荐系统，支持多源异构信息抓取、RSS 聚合、网页正文抽取、中文时间解析、机会分类打分、去重入库和邮件自动推送。
```

---

## 23. 参考文档

- GitHub Actions Workflow Syntax：<https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions>
- GitHub Actions Secrets：<https://docs.github.com/en/actions/concepts/security/secrets>
- feedparser：<https://pypi.org/pypi/feedparser>
- RSSHub Docs：<https://docs.rsshub.app/>
- Python smtplib：<https://docs.python.org/3/library/smtplib.html>
- BeautifulSoup：<https://beautiful-soup.readthedocs.io/>
