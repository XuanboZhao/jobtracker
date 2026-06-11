# Job Desk — 个人岗位追踪（轻版本）

一个每天自动跑的岗位追踪器：从目标公司的招聘系统拉取在招岗位，按关键词/类别筛选，
区分「本周新增」与「仍在招（存档）」，并通过一个看板追踪你的申请状态。

## 它解决的两件事
1. **不遗忘**：每个岗位记 `first_seen` / `last_seen`。只要它还出现在抓取结果里就算「在招」；
   一旦从官网消失（申请期结束）才标记关闭。所以你既能看到「新增」，也不会丢掉一周前开放、现在仍可投的岗位。
2. **申请追踪 + 分区**：看板可按申请状态（未申请 / 已申请 / 测评 / 面试 / Offer / 已拒）追踪，
   并按公司类别和岗位类别筛选。申请状态保存在浏览器本地，**每日刷新数据不会覆盖你的进度**。

## 结构
```
config/companies.yaml   目标公司 → 招聘系统 + token + 类别（加公司=加一行）
config/filters.yaml     关键词（必）+ 地点/资历/排除词（可选，默认关）
jobtracker/adapters.py  按"系统"写的取数器：greenhouse / lever（真实）+ custom（占位）
jobtracker/classify.py  从标题判断岗位类别 + 资历
jobtracker/storage.py   SQLite：first_seen/last_seen、新增 vs 存档、消失即关闭
jobtracker/pipeline.py  入口：抓取→筛选→入库→导出 data.json→邮件
dashboard/index.html    看板（读 data.json；本地保存申请状态）
.github/workflows/daily.yml  每天 06:00 UTC 自动跑，并把数据 commit 回仓库
```

## 本地运行
```bash
pip install -r requirements.txt
python -m jobtracker.pipeline      # 写出 jobs.db 和 dashboard/data.json
# 打开 dashboard/index.html 即可（建议本地起个静态服务以加载 data.json）
python -m http.server -d dashboard 8000   # 然后访问 http://localhost:8000
```

## 云端每天自动跑（GitHub Actions）
1. 把这个仓库推到 GitHub。
2. 在 Settings → Secrets and variables → Actions 里加邮件密钥（用 Gmail 应用专用密码）：
   `SMTP_USER`、`SMTP_PASS`、`MAIL_TO`（可选 `SMTP_HOST`/`SMTP_PORT`）。
3. Actions 标签页可手动点 `Run workflow` 立即测试；之后每天 06:00 UTC 自动跑，
   把刷新后的 `jobs.db` 和 `data.json` commit 回仓库。

> 注意：cron 用 UTC。`0 6 * * *` = 荷兰夏令时 08:00。

## 四家公司的真实状态（诚实说明）
| 公司 | 招聘系统 | 状态 |
|---|---|---|
| IMC | Greenhouse（token `imc`） | ✅ 适配器就绪，`enabled: true` 即可拉实时数据 |
| Optiver | 自建站，未发现公开 JSON 接口 | ⏳ 需再侦察一次，或用 Playwright 兜底 |
| ASML | 大概率 Workday/SuccessFactors 级 | ⏳ 需确认 tenant 地址后写适配器 |
| Robeco | 待确认 | ⏳ 同上 |

看板与流水线本身**与公司无关**——只要某家的适配器接通，它就自动进入同一套新增/存档/状态流程。
当前 `dashboard/data.json` 是示例数据，用于让你立刻看到成品；接通后会被实时数据替换。

## 下一步（养成长期工具时）
- 把 Optiver/ASML/Robeco 的真实接口接上（每家一次性）。
- 导出 Excel、或把 `data.json` 同步到 Google Sheet 做云端看板。
- 看板增加备注、截止日期、拖拽排序。
