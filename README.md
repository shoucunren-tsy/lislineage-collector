# 图情谱系学者数据采集 · LIS Lineage Collector

给 [LIS LINEAGE](https://lislineage.com) 采集学者资料的可分发工具包：**统一字段 → 逐条溯源 → 机器校验 → 人工合并**。

它解决的问题不是「怎么搜」，而是「搜完怎么交」。采集人拿到的是一份有模板、有校验、有验收标准的任务包；维护者拿回的是一份结构固定、可以直接比对合并的数据包。

## 适合谁

- 把学者资料采集分发给同学/助研/外包的人；
- 多人协作、需要合并同一份站点数据的人；
- 想复核已有题录和履历出处的人。

## 核心约定

1. **一位学者一个文件夹**，文件夹名即站点稳定 ID；一位采集人可以负责多位学者。**站点上已有页面的学者不采**（开工前搜一下姓名即可，快速判断）。
2. **每条记录都有 `source_id`**，来源表里写 URL、访问日期、原文摘录；关键页面存快照。
3. **未知就是未知**：被引查不到写 `unknown`/`blocked`，不许写 0。
4. **不许宣称收齐**：必须写边界与缺口，覆盖等级 A/B/C 与审计记录挂钩。
5. **单点检索约 5–10 分钟搜不到就停**，记 `unknown`/`pending` 后继续下一条，不反复硬搜。
6. **采集人不碰站点文件**，只交原料，由维护者合并。交回时**每位学者一个 zip**。

完整契约见 [SKILL.md](SKILL.md)，字段见 [references/fields.md](references/fields.md)，教程见 `docs/使用教程.docx`。

## 快速开始

```bash
git clone <本仓库地址> lislineage-collector
cd lislineage-collector

# 生成任务包：一位采集人 + 两位学者
# --out 换成你电脑上的任意工作目录，下面只是示例
python scripts/gen_task.py \
  --out "工作夹/B01_张三" \
  --batch B01 --collector 张三 \
  --scholars fenghuiling:冯惠玲,huchangping:胡昌平

# 采集完成后自查
python scripts/validate_package.py "工作夹/B01_张三"

# 通过后生成文件哈希，并把 submitted_at 更新为打包当天
python scripts/pack.py "工作夹/B01_张三"
```

`python` 需 3.9+，只用标准库，无需安装依赖。

没有 Python：浏览器打开 `checker/index.html`，把学者文件夹拖进去即可自查。

## 交付物长什么样

```
B01_张三/
└── fenghuiling/
    ├── profile.csv
    ├── sources.csv
    ├── career.csv
    ├── papers_cn.csv
    ├── papers_intl.csv
    ├── activities.csv
    ├── relations.csv
    ├── books.csv
    ├── rejects.csv
    ├── audit.csv
    ├── manifest.json
    ├── report.md
    └── evidence/
        ├── S001.html
        └── S002.pdf
```

同批次多位学者就在 `B01_张三/` 下并列多个学者文件夹。存放路径随你定。交回时**每位学者的文件夹单独压成一个 zip** 发给维护者，传输方式不限。

## 接入不同 Agent

| 工具 | 放置方式 | 读取入口 |
|---|---|---|
| Claude Code | 把本目录放到 `~/.claude/skills/`（或建立目录链接） | `SKILL.md` |
| Codex | 把本目录作为工作目录打开，或在其 `AGENTS.md` 中引用 | `AGENTS.md` |
| WorkBuddy | 作为知识库/工作区导入 | `AGENTS.md` 或 `README.md` |
| 其他 Agent | 任意方式打开仓库 | 先读 `AGENTS.md`，再按需读 `references/` |

核心逻辑不依赖任何平台：契约在 `schema/fields.json`，校验在 `scripts/`，文档在 `references/`。Agent 只是执行者。

## 校验器检查什么

- 目录与文件齐全、CSV 编码与列名一致
- 枚举值合法、必填字段非空
- 所有 `source_id` 能在来源表找到
- 论文作者列表包含本学者
- 被引状态与数值一致（未知不许写 0）
- 履历 confirmed 必须有一手来源与摘录
- 审计闭合：`total` = `returned` = `unique_ids`，或写明未闭合原因
- 覆盖等级与审计记录一致（有 open 渠道就不能评 A）
- 报告中的绝对化表述（可识别否定语境）
- 证据快照可检索时，摘录能在快照中找到

## 目录说明

| 路径 | 内容 |
|---|---|
| `SKILL.md` | Claude Code 技能入口，含硬规则 |
| `AGENTS.md` | 通用 Agent 入口 |
| `schema/fields.json` | 唯一字段契约，校验器与生成器都读它 |
| `references/` | 字段手册、来源规则、工作流、事故案例、非技术手册 |
| `templates/` | 空表模板与报告模板 |
| `scripts/` | `gen_task.py` 生成任务包、`validate_package.py` 校验、`pack.py` 出哈希 |
| `checker/index.html` | 离线自查页，无 Python 也能用 |
| `examples/` | 完整示例包（虚构学者，仅演示格式） |
| `docs/使用教程.docx` | 面向采集人的图文教程 |

## 边界

- 本工具包不替采集人判断学术价值，只约束「怎么记录、怎么举证」。
- 不保证任何渠道可访问；渠道受限时按 `blocked` 记录，不视为零。
- 不包含站点合并脚本；合并由维护者按站点 SOP 执行。
- 示例中学者与 URL 均为虚构占位，不是真实数据。

## 许可

脚本与模板：MIT。文档与教程：CC BY 4.0。
