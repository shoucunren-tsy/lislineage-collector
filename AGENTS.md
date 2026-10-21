# AGENTS.md · 通用 Agent 接入说明

本仓库是「图情谱系学者数据采集」工具包。无论使用 Claude Code、Codex、WorkBuddy 还是其他 Agent，都按下面的顺序读取与执行。

## 读取顺序

1. 本文件（定位与边界）
2. `SKILL.md`（交付契约与硬规则）
3. `references/fields.md`（逐列字段定义）
4. `references/sourcing-rules.md`（来源、摘录、快照、被引口径）
5. `references/workflow.md`（分步操作与渠道检索）
6. `references/rejection-cases.md`（做判定前必读）
7. `schema/fields.json`（机器可读契约，写脚本时以它为准）

## 执行任务时的固定动作

0. 开工前到 lislineage.com 搜姓名：已经有页面的学者跳过、不采（快速判断，不深究）。
1. 用 `scripts/gen_task.py` 生成任务包，不要手工建空表。
2. 采集过程中边做边填 `sources.csv`，不要最后补来源。
3. 每完成一个渠道，立刻在 `audit.csv` 记一行（总数、返回数、唯一数、是否末页、是否闭合）。
4. 排除的对象写 `rejects.csv`，写清依据。
5. 收尾跑 `scripts/validate_package.py`，有错误必须改到通过；警告逐条判断。
6. 通过后跑 `scripts/pack.py` 生成哈希清单，再把每位学者的文件夹单独压成 zip。
7. 不要修改站点端的 `data.js`、`papers.js`、`profiles.js`、`changelog.html`、`cover-data.js`。

## 效率约束

- **单点检索限时止损**：为一条事实（一本书的 ISBN、一个出版日期、一个被引数）检索约 5–10 分钟仍无结果，立刻停，记 `unknown`/`pending` 后继续下一条。禁止换词硬搜、禁止多渠道轮询同一项。
- 例外：身份未定住（同名未排除、单位对不上）时整个停下来核实，不算止损。
- 工作目录与输出路径由用户机器决定，不要写死盘符或固定文件夹名。

## 硬性禁止

- 不编造 URL、页码、DOI、被引次数、导师、获奖；
- 不把未知写成 0；
- 不宣称「全部收齐 / 穷尽 / 无遗漏」；
- 不把同名同姓、导师挂名、媒体稿、书籍章节重复计入论文；
- 不为单条事实无限期检索（见「效率约束」）；
- 不删除别人的记录来「让校验通过」，有冲突写进 `notes` 和 `rejects.csv`。

## 文件写入要求

- CSV 用 UTF-8（可带 BOM），逗号分隔，单元格内不换行；
- 列名与列顺序严格按 `schema/fields.json`；
- 一位学者一个文件夹，文件夹名 = `scholar_id`；
- 证据快照放在 `evidence/`，文件名与 `source_id` 对应。

## 输出给用户的顺序

先报「校验结果（错误/警告数）」，再报「覆盖等级与主要缺口」，最后报「产物路径」。不要用「已完成」概括未验证的工作。
