---
name: lislineage-collector-图情谱系学者数据采集
description: 按统一交付契约逐位采集图情领域学者的论文、教育与任职履历、活动动态和学术关系，产出带来源编号、逐字摘录与证据快照的 CSV 数据包，并在本地跑校验器自查后交给 LIS LINEAGE 维护者合并。
---

# 图情谱系学者数据采集

把「翻到的网页」变成「能核对、能合并、能追责的数据」。

## 何时使用

- 需要为 lislineage.com 采集一位或多位图情档领域学者的资料；
- 需要把采集任务分发给多人，收回后能机器校验再合并；
- 需要复核一批题录/履历的归属与出处。

**开工前先查重**：到 lislineage.com 搜一下姓名，已经有页面的学者跳过、不采。这一步快速判断即可（一两分钟），不深究、不做二次核实；拿不准就先问维护者。

## 交付契约（不可改）

一位学者一个文件夹，文件夹名就是学者ID。一个采集人可以负责多位学者，仍然一位一个文件夹。

```
B01_张三/
└── fenghuiling/
    ├── profile.csv          学者身份（只有1行数据）
    ├── sources.csv          来源登记表（所有表靠 source_id 指向这里）
    ├── career.csv           教育与任职时间线
    ├── papers_cn.csv        中文论文
    ├── papers_intl.csv      外文论文（英/日/韩等）
    ├── activities.csv       活动动态
    ├── relations.csv        学术关系
    ├── books.csv            专著/教材/译著/书章
    ├── rejects.csv          排除项留痕
    ├── audit.csv            检索审计（每个渠道查了什么、是否闭合）
    ├── manifest.json        批次、覆盖等级、边界、文件哈希
    ├── report.md            人读报告
    └── evidence/            证据快照（HTML/PDF/截图/文本）
```

- 10 张 CSV + manifest.json + report.md + evidence/ 必须齐全。没有数据的表保留表头即可，不要删表。
- 表头列名、列顺序以 `schema/fields.json` 为准，不一致直接校验失败。
- 文件一律 UTF-8（带不带 BOM 都接受），不要用 GBK 另存。
- CSV 单元格内不换行；确实需要多句时用「；」连接。
- 不要改站点文件（data.js / papers.js / profiles.js / changelog.html / cover-data.js）。采集包只是原料。

## 硬规则

1. **每条事实都要有出处。** 出处写在 sources.csv，业务行用 `source_id` 引用，`excerpt` 填页面上能证明这条记录的原句，至少 6 个字。没有地址的「听说」「应该」不进表。
2. **区分一手与二手。** 官网、期刊页、ORCID、OpenAlex 原始记录、会议官网 = 一手；百科、聚合站、转载新闻、公众号转述 = 二手。二手来源不能单独支撑 `career.status=confirmed`。
3. **论文必须写清来源渠道。** `db_source` 填实际看到题录的地方（期刊官网 / 知网 / 万方 / OpenAlex / Crossref ...），不要写「网络」。
4. **被引次数未知绝不填 0。** 页面打不开、被 WAF 挡、需要登录 → `cited_status=blocked` 或 `unknown`，`cited` 留空。只有页面上明确写 0 才用 `verified_zero`。
5. **同名必须排除并留痕。** 查过但判定不是本人的，写进 rejects.csv，写清依据。宁可 pending，不可硬塞。
6. **履历不靠学制倒推。** 官方只写博士毕业年，就只写毕业年；入学年查不到留空。受聘事件不要延伸到「至今」。
7. **书籍与书章不混算。** 一部专著和它的章节分别登记时，在 notes 写明拆分关系，不要当成两项独立成果。
8. **连载按组登记。** 同一组连载文章按实际刊期分别登记，并在 notes 标注组名，不合并成一篇，也不重复计数。
9. **不许宣称收齐。** 报告里写清边界与缺口。出现「全部收齐 / 穷尽 / 完整收录 / 无遗漏」这类断言，校验器会拦。
10. **不许编造。** 编 URL、编页码、编被引、编导师都算数据事故。查不到就写查不到。
11. **单点检索限时止损。** 为一条事实（一本书的 ISBN、一个出版日期、一个被引数）检索约 5–10 分钟仍无结果，立刻停：不再换词硬搜、不再换渠道轮询。该字段留空或记 `unknown`/`pending`，写进「边界与缺口」，继续下一条。反复搜同一项既费时间也费 token。例外：身份没定住（同名未排除、单位对不上）不属于止损范围——人没对上就整个停下来，不能边猜边收。

## 工作流（一位学者）

按顺序做，每步都有产物。

| 步 | 做什么 | 产物 |
|---|---|---|
| 0 | 查重（站点已有页面则跳过）→ 确认身份：姓名、单位、研究方向、同名风险 | profile.csv 初稿、rejects.csv |
| 1 | 来源普查：官网主页、院系页、ORCID、OpenAlex、期刊作者页、公众号、会议页 | sources.csv、audit.csv |
| 2 | 中文论文：期刊官网目录逐期核 / 知网 / 万方 / ncpssd；记卷期页 DOI | papers_cn.csv |
| 3 | 外文论文：OpenAlex 按作者ID + DOI 反查、Crossref、会议官网；排除同名 | papers_intl.csv |
| 4 | 被引：优先来源页自带计数；能取则 verified，不能取则 unknown/blocked | 填 cited_* 列 |
| 5 | 履历：官方简介、CV、导师页、任职公告、学位论文库；逐段配来源 | career.csv |
| 6 | 活动动态：用 WebSearch 跨渠道搜，单位新闻、公众号、会议、获奖、评审都要过 | activities.csv |
| 7 | 关系与著作：师承看导师页/致谢/官方简介；合著看作者序列；著作看版权页/OPAC | relations.csv、books.csv |
| 8 | 检索闭合：每个渠道记录总数、返回数、唯一数、是否末页 | audit.csv |
| 9 | 自查、写报告、打包 | manifest.json、report.md、evidence/ |

详细操作见 `references/workflow.md`；字段逐列说明见 `references/fields.md`；来源与证据规则见 `references/sourcing-rules.md`；常见坑见 `references/rejection-cases.md`。

## 覆盖等级（manifest.coverage）

| 级 | 含义 | 硬性要求 |
|---|---|---|
| A | 主渠道都查了且闭合 | 该维度至少 1 条记录，且至少 1 条 `closure=closed` 的审计 |
| B | 主渠道覆盖但存在未闭合或受限 | 该维度至少 1 条记录，报告写明受限点 |
| C | 仅探索性检索 | 只能作为线索，报告必须写明未覆盖范围 |

规则：只要有 `closure=open` 的审计，该维度最高只能 B；A 级不允许同时存在未闭合渠道。

## 命令

输出目录按你电脑上的习惯来（桌面、D 盘、任意工作夹都行），下面路径只是示例。

```bash
# 1. 生成任务包（每位采集人一份）
python scripts/gen_task.py --out "工作夹/B01_张三" --batch B01 --collector 张三 \
  --scholars fenghuiling:冯惠玲,huchangping:胡昌平

# 2. 采集完成后自查（指向批次目录或单个学者目录都可）
python scripts/validate_package.py "工作夹/B01_张三"

# 3. 通过后生成哈希清单（submitted_at 会自动更新为打包当天）
python scripts/pack.py "工作夹/B01_张三"
```

无 Python 环境的采集人：用浏览器打开 `checker/index.html`，把学者文件夹拖进去自查（覆盖结构、表头、枚举、source_id 引用、被引一致性、绝对化措辞）。最终仍以维护者跑脚本为准。

## 交付前自查清单

- [ ] 每个 source_id 都在 sources.csv 里，且都被业务表用到
- [ ] 每条论文都含本学者姓名（作者列表里能查到）
- [ ] 被引为空的记录都有 unknown/blocked 状态，且没有 0 冒充未知
- [ ] 每条履历 confirmed 都有一手来源 + 原句
- [ ] 每个渠道在 audit.csv 有记录，未闭合的都写了原因
- [ ] rejects.csv 登记了查过但排除的对象
- [ ] report.md 写了「边界与缺口」
- [ ] manifest.coverage 与实际审计一致
- [ ] 没有「全部收齐 / 穷尽 / 无遗漏」类表述
- [ ] 跑过 validate_package.py，结果为通过

## 传给维护者

**每位学者的文件夹单独压成一个 zip 发过来**（zip 根就是该学者文件夹，内含全部 CSV、manifest.json、report.md、evidence/）。一位学者一个压缩包，不要把多位学者塞进同一个 zip，也不要只压其中几张表。

- 存放路径随你定，交回时给的是学者文件夹的压缩包；
- 不要改文件名、不要加「最终版」「(1)」「副本」后缀；
- 传输方式不限（网盘、微信、邮件都行）。

维护者收到后：解压 → 跑 `validate_package.py` → 抽查 evidence 快照 → 合并进站点 → 再跑站点校验。

## 参考文件

| 文件 | 用途 |
|---|---|
| `references/fields.md` | 每张表每一列的含义、必填、枚举、示例 |
| `references/sourcing-rules.md` | 来源分级、摘录写法、快照、冲突处理、被引口径 |
| `references/workflow.md` | 分步操作、各渠道检索式、闭合判断 |
| `references/rejection-cases.md` | 真实事故清单：同名、导师挂名、连载、被引 0 等 |
| `references/collector-handbook.md` | 非技术版：Excel/WPS 填表、保存编码、常见报错 |
| `docs/使用教程.docx` | 图文教程，发给采集人 |
| `AGENTS.md` | Codex 等通用 Agent 的接入说明 |
