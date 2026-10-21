# 任务：{{学者姓名}}（{{scholar_id}}）

- 批次：{{batch}}
- 采集人：{{collector}}
- 生成日期：{{生成日期}}
- 工具包版本：{{contract_version}}

## 交付目录

本目录就是一位学者的完整交付单元。保持目录结构和文件名不变：

```
{{scholar_id}}/
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
```

## 执行顺序

0. 先到 lislineage.com 搜姓名：**已经有页面的学者跳过、不采**（快速判断即可，拿不准问维护者）。
1. 读 `references/workflow.md` 第 0–9 步，按顺序做。
2. 先建来源，再写记录：所有业务行的 `source_id` 必须能在 `sources.csv` 找到。
3. 每个渠道查完立刻写 `audit.csv`（总数、返回数、唯一数、末页、闭合）。
4. 排除的对象写 `rejects.csv`，写清依据。
5. 收尾：
   - 填 `manifest.json` 的 `coverage`（A/B/C）、`boundaries`（至少 1 条）、`gaps`；
   - 写 `report.md`，必须有「边界与缺口」小节；
   - 跑 `python scripts/validate_package.py <本批次目录>`，错误清零；
   - 跑 `python scripts/pack.py <本批次目录>` 生成哈希；
   - 把**每位学者的文件夹单独压成一个 zip** 交回。

## 红线

- 不编 URL、页码、DOI、被引、导师、获奖、日期。
- 未知写 `unknown`，受限写 `blocked`，不写 0。
- 不宣称「全部收齐 / 穷尽 / 无遗漏」。
- 不改站点文件，只交原料。
- **单点检索约 5–10 分钟搜不到就停**，记 `unknown`/`pending` 后继续下一条，不反复硬搜同一项。

## 自查清单

- [ ] 10 张 CSV + manifest.json + report.md + evidence/ 齐全
- [ ] 每条记录都有 source_id 与摘录
- [ ] 每条论文的作者列表含本学者
- [ ] 被引状态与数值一致
- [ ] 履历 confirmed 有一手来源
- [ ] audit 记录了每个渠道，未闭合的都写了原因
- [ ] rejects 登记了查过但排除的对象
- [ ] manifest 的覆盖等级与审计一致
- [ ] 校验器通过
