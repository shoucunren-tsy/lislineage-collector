# 字段说明

机器可读版本：`schema/fields.json`。两者冲突时以 `schema/fields.json` 为准（校验器读它）。

通用约定：

- 空值就留空，不要写「无」「null」「-」「暂无」。确实需要说明的写进 `notes`。
- 多个值用 `|` 分隔（作者、变体名、共同作者）。
- 日期：`YYYY-MM-DD`；只能确定到月写 `YYYY-MM`；只能确定到年写 `YYYY`；在职写 `至今`。
- 编号：`C001`、`P001`、`A001`、`R001`、`B001`、`X001`、`Q001`，在本学者文件夹内唯一，删行后不要重排。
- `scholar_id` 在所有表里必须等于文件夹名。

---

## profile.csv · 学者身份

只有 **1 行数据**。多行直接判错。

| 列 | 必填 | 说明 | 示例 |
|---|---|---|---|
| scholar_id | 是 | 稳定 ID，`^[a-z][a-z0-9_]{2,31}$` | `example_scholar` |
| name_cn | 是 | 中文姓名，与官方页面一致 | `示例学者` |
| name_en | 否 | 英文名或拼音，官方写法优先 | `Shili Xuezhe` |
| name_variants | 否 | 曾用名、异体、检索变体，用竖线分隔 | `示例学者\|Shili Xuezhe` |
| institution | 是 | 当前主要任职机构全称 | `示例大学` |
| department | 否 | 院系全称 | `信息管理学院` |
| role | 否 | 职务职称，多项用竖线分隔 | `教授\|博士生导师` |
| research_fields | 否 | 研究方向，`、` 分隔 | `文献计量、科学评价` |
| homepage | 否 | 官方个人主页 | `https://example.edu.cn/faculty/xuezhe` |
| orcid | 否 | ORCID | `0000-0002-1825-0097` |
| openalex_id | 否 | OpenAlex 作者 ID | `A5023888391` |
| intro_zh | 否 | 150 字内客观简介，只写可证事实 | `示例大学信息管理学院教授，从事文献计量研究。` |

`name_variants` 直接影响后续「作者列表是否含本人」的检查，务必把常见写法都列上。

---

## sources.csv · 来源登记表

所有业务表的 `source_id` 都指向这里。**先登记来源，再写记录。**

| 列 | 必填 | 说明 |
|---|---|---|
| source_id | 是 | `S001` 起，不复用 |
| source_type | 是 | 见枚举 |
| source_tier | 是 | `一手` / `二手` |
| title | 是 | 页面或文件标题，照抄 |
| publisher | 否 | 发布方 |
| url | 是 | 完整 http/https URL；纸质资料写馆藏描述 |
| accessed_at | 是 | 访问日期 `YYYY-MM-DD` |
| snapshot | 否 | `evidence/S001.html`，相对本学者文件夹 |
| notes | 否 | 403/WAF/需登录/语言/转载关系 |

`source_type` 枚举：`官方主页`、`院系页`、`个人主页`、`ORCID`、`OpenAlex`、`Crossref`、`期刊官网`、`数据库`、`新闻`、`微信公众号`、`会议官网`、`学位论文库`、`出版社`、`其他`

示例：

```csv
source_id,source_type,source_tier,title,publisher,url,accessed_at,snapshot,notes
S001,院系页,一手,示例学者-师资队伍,示例大学信息管理学院,https://example.edu.cn/faculty/xuezhe,2026-10-21,evidence/S001.html,
S002,OpenAlex,一手,Shili Xuezhe,OpenAlex,https://openalex.org/authors/A5023888391,2026-10-21,evidence/S002.json,
```

---

## career.csv · 教育与任职时间线

一行一段经历。学位、任职、兼职分别成行。

| 列 | 必填 | 说明 |
|---|---|---|
| career_id | 是 | `C001` 起 |
| scholar_id | 是 | 等于文件夹名 |
| start | 否 | 开始时间；未知留空 |
| end | 否 | 结束时间；在职写 `至今` |
| institution | 是 | 机构全称 |
| department | 否 | 院系/专业 |
| degree_or_role | 是 | `本科`/`硕士`/`博士`/`博士后`/`教授`/`副院长` 等 |
| advisor | 否 | 仅官方明确写出才填 |
| source_id | 是 | status=unknown 时可为空 |
| excerpt | 是 | 原句摘录（≥6 字）；status=unknown 时可为空 |
| status | 是 | `confirmed` / `candidate` / `unknown` |
| notes | 否 | 冲突、口径、存疑 |

规则：

- `confirmed` 必须有一手来源；只有二手来源会报警告。
- 不要按学制倒推入学年。官方只写毕业年，就只填 `end=1997`，`start` 留空，notes 写「起止年未载」。
- 单点事件（受聘、获奖）`start=end`。受聘事件不要写成「至今」。
- 同一机构连续多段职务可以合并，但学位与职务不要合并。

---

## papers_cn.csv · 中文论文

| 列 | 必填 | 说明 |
|---|---|---|
| paper_id | 是 | `P001` 起 |
| scholar_id | 是 | 等于文件夹名 |
| title | 是 | 照抄标题 |
| authors | 是 | 完整作者序列，用竖线分隔，含本学者 |
| journal | 是 | 期刊全称 |
| year | 是 | 四位年份；确无年份留空且 notes 以「缺年:」开头 |
| volume | 否 | 卷 |
| issue | 否 | 期 |
| pages | 否 | `45-58` 或文章号 |
| doi | 否 | 不带 `https://doi.org/` |
| url | 否 | 题录页/全文页 |
| db_source | 是 | 见枚举 |
| source_id | 是 | 指向 sources.csv |
| excerpt | 是 | 页面上证明本题录的原句（≥6 字） |
| cited | 否 | 非负整数；未知留空 |
| cited_source | 否 | `知网`/`万方`/`OpenAlex` 等 |
| cited_url | 否 | 被引页面 |
| cited_date | 否 | 抓取日期 |
| cited_status | 是 | 见下方口径 |
| action | 是 | `new` / `correction` |
| notes | 否 | 归属疑点、同名排除 |

`db_source` 枚举：`期刊官网`、`知网`、`万方`、`维普`、`国家哲学社会科学文献中心`、`OpenAlex`、`Crossref`、`会议官网`、`出版社`、`其他`

`cited_status` 口径：

| 值 | 含义 | cited |
|---|---|---|
| verified | 来源页直接给出被引数 | 必填非负整数 |
| recorded_value | 二手聚合页给出数值，未回原始库核实 | 必填非负整数 |
| verified_zero | 来源页明确显示 0 | 必须为 0 |
| unknown | 渠道查不到，或数量不可靠 | 必须留空 |
| blocked | 页面 403/WAF/需登录/超时 | 必须留空 |

---

## papers_intl.csv · 外文论文

列与 `papers_cn.csv` 相同，额外多三列：

| 列 | 必填 | 说明 |
|---|---|---|
| venue | 是 | 期刊/会议/出版社全称 |
| venue_type | 是 | `journal` / `conference` / `book_chapter` / `preprint` |
| language | 是 | `en` / `ja` / `ko` / `other` |

注意：

- 非中文文献都进这张表，不止英文。
- 书名章节若属于独立论文，进本表并标 `book_chapter`；若属于专著整体，进 books.csv。同一内容不要两边都算。
- OpenAlex 的 `display_name` 可能被改写，标题以出版页为准。

---

## activities.csv · 活动动态

| 列 | 必填 | 说明 |
|---|---|---|
| activity_id | 是 | `A001` 起 |
| scholar_id | 是 | 等于文件夹名 |
| date | 是 | 活动日期；可降级到月/年 |
| type | 是 | 见枚举 |
| title | 是 | 活动名/报道标题 |
| organizer | 否 | 主办方 |
| location | 否 | 地点 |
| account_name | 否 | 公众号名称（来源为公众号时） |
| article_title | 否 | 原文标题（与活动名不同时） |
| article_url | 否 | 原文链接 |
| source_id | 是 | 指向 sources.csv |
| excerpt | 是 | 证明该学者出现的原句（≥6 字） |
| notes | 否 | 转载关系、日期存疑 |

`type` 枚举：`讲座`、`会议`、`获奖`、`评审`、`任职`、`访谈`、`悼念`、`学科建设`、`培训`、`其他`

规则：

- 同一活动被多家转载只登记一次，来源选最原始的一手页面，其余在 notes 记「另见」。
- 只有姓名出现、无法确认是本人才不进表；可先写 rejects.csv 的 pending。
- 日期只能确定到月就写 `YYYY-MM`，不要编日。

---

## relations.csv · 学术关系

| 列 | 必填 | 说明 |
|---|---|---|
| relation_id | 是 | `R001` 起 |
| scholar_id | 是 | 本学者（边的起点） |
| other_name | 是 | 关系人 |
| other_scholar_id | 否 | 对方站点 ID，不确定留空 |
| relation_type | 是 | 见枚举 |
| start | 否 | 关系开始年 |
| end | 否 | 关系结束年 |
| evidence_url | 否 | 额外证据页 |
| source_id | 是 | 指向 sources.csv |
| excerpt | 是 | 证明关系的原句（≥6 字） |
| notes | 否 | 方向、存疑 |

`relation_type` 枚举：`博士师承`、`硕士师承`、`博士后`、`合著`、`同事`、`其他`

规则：

- 师承类：**本学者是被指导方**，`other_name` 是导师。方向写反会造成整张图错。
- 只凭「同单位」不能判同事；要有共事、同部门、合作项目的明确表述。
- 合著边建议只登记有明确合作关系的长期合著者，或重要成果的合著者，并在 notes 写依据；不要把所有共同署名都做成边。

---

## books.csv · 著作

| 列 | 必填 | 说明 |
|---|---|---|
| book_id | 是 | `B001` 起 |
| scholar_id | 是 | 等于文件夹名 |
| title | 是 | 书名，照抄版权页 |
| subtitle | 否 | 副标题 |
| publisher | 是 | 出版社全称 |
| year | 是 | 四位年份 |
| isbn | 否 | 保留原格式 |
| role | 是 | 见枚举 |
| coauthors | 否 | 其他责任者，用竖线分隔 |
| source_id | 是 | 指向 sources.csv |
| excerpt | 是 | 版权页/书目页原句 |
| notes | 否 | 版次、丛书、拆分关系 |

`role` 枚举：`独著`、`第一作者`、`合著`、`主编`、`副主编`、`参编`、`译著`、`章节`

---

## rejects.csv · 排除项

**查过但不要的，也要留痕。** 这是下一批采集人最值钱的部分。

| 列 | 必填 | 说明 |
|---|---|---|
| reject_id | 是 | `X001` 起 |
| scholar_id | 是 | 等于文件夹名 |
| object_type | 是 | `paper`/`career`/`activity`/`relation`/`book`/`profile` |
| identifier | 是 | DOI/URL/年份+题名 |
| title | 否 | 对象标题 |
| reason | 是 | 见枚举 |
| evidence | 是 | 排除依据（原句或链接） |
| status | 是 | `rejected` / `pending` |
| notes | 否 | 补充 |

`reason` 枚举：`同名不同人`、`导师署名误挂`、`媒体稿非论文`、`连载拆分`、`书籍章节重复计算`、`作者列表无本人`、`聚合页无原始出处`、`主题不符`、`身份未确认`、`其他`

---

## audit.csv · 检索审计

记录「查了什么、返回多少、有没有翻完」。没有审计的覆盖等级不算数。

| 列 | 必填 | 说明 |
|---|---|---|
| audit_id | 是 | `Q001` 起 |
| scholar_id | 是 | 等于文件夹名 |
| dimension | 是 | `papers_cn`/`papers_intl`/`career`/`activities`/`relations`/`books` |
| channel | 是 | 渠道名 |
| query | 是 | 实际检索式或 URL |
| date | 是 | `YYYY-MM-DD` |
| total | 否 | 渠道报告总数，不提供则留空 |
| returned | 是 | 实际取回条数 |
| unique_ids | 是 | 去重后唯一条数 |
| last_page | 是 | `true` / `false` |
| closure | 是 | `closed` / `open` |
| note | 否 | 未闭合原因、403、验证码、需登录 |

闭合判定：

- `closed`：翻到最后一页，`returned = unique_ids`，且 `total` 为空或 `total = returned`。
- `open`：任一条不满足，必须在 `note` 写原因。

示例：

```csv
audit_id,scholar_id,dimension,channel,query,date,total,returned,unique_ids,last_page,closure,note
Q001,example_scholar,papers_intl,OpenAlex Author,https://api.openalex.org/works?filter=author.id:A5023888391&per-page=200,2026-10-21,57,57,57,true,closed,
Q002,example_scholar,papers_cn,万方作者页,作者=示例学者,2026-10-21,,0,0,false,open,WAF 拦截 403，未取到列表
```

---

## manifest.json

```json
{
  "contract_version": "1.0.0",
  "batch": "B01",
  "collector": "张三",
  "scholar_id": "example_scholar",
  "scholar_name": "示例学者",
  "submitted_at": "2026-10-25",
  "coverage": {
    "papers_cn": "B",
    "papers_intl": "A",
    "career": "B",
    "activities": "C",
    "relations": "C",
    "books": "C"
  },
  "boundaries": [
    "万方作者页 WAF 拦截，中文被引以来源页自带计数为准，未取到的保持 unknown"
  ],
  "gaps": [
    "外文会议论文仅覆盖 OpenAlex 收录部分"
  ],
  "files": [
    {"name": "papers_cn.csv", "rows": 12, "sha256": "..."}
  ]
}
```

要求：

- `boundaries` 至少 1 条，写具体受限点，不写「尽力了」。
- `gaps` 可以空数组，但 `boundaries` 不能空。
- `files` 由 `scripts/pack.py` 生成，可先留空数组。
- 出现占位文字（`待填写`、`TODO`）直接判错。

---

## report.md

面向人读，建议固定小节：

```markdown
# 示例学者 · 采集报告

## 基本信息
## 覆盖范围与等级
## 来源清单（一手/二手）
## 关键判断（排除项与疑难）
## 边界与缺口
## 复现步骤（检索式与日期）
```

「边界与缺口」必须落笔，校验器会检查该小节是否存在。不要写「已全部收齐」这类表述，否定语境除外。
