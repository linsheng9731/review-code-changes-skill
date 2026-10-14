# Code Review 助手

审查 PR、分支、提交和本地代码改动的 Agent Skill。默认中文，代码标识符保留原文。

## 能力

- 按具体行为变化聚合核心改动，区分非核心改动。
- 绘制受影响的核心流程，追踪调用、数据与失败路径。
- 区分已确认问题与待验证风险，提供通俗解释、触发例子和验证方法。
- 为每个改动块说明意图、作用、必要性和审查结论。
- 输出离线 HTML 与 Markdown 报告。HTML 包含固定目录、左右红绿 diff，以及与代码绑定的说明。
- 核对逐处覆盖清单，记录测试结果和审查限制。

## 安装

```bash
git clone https://github.com/linsheng9731/review-code-changes-skill.git
```

将仓库中的 `review-code-changes/` 完整目录复制到你的 Agent 支持的 skills 目录。保留脚本、参考文档、报告模板和界面元数据，不要只复制 `SKILL.md`。如已安装同名技能，请先备份再更新。

## 使用

```text
使用 $review-code-changes 审查这个 PR：<PR URL>
使用 $review-code-changes 审查当前仓库的本地改动。
使用 $review-code-changes 审查指定 base/head 的分支改动。
```

以真实 diff 和上下文为依据。默认不修改被审查代码，也不发布评论、合并或部署。

## 文件结构

```text
review-code-changes/
├── SKILL.md
├── agents/openai.yaml
├── assets/
│   ├── change-group.html
│   ├── icon.svg
│   ├── report.html
│   └── review-unit.html
├── references/
│   ├── report-contract.md
│   └── review-rules.md
└── scripts/
    ├── collect_changes.py
    └── render_diff.py
```

## 脚本

脚本使用 Python 3 和标准库；采集改动还需要 Git。

```bash
python3 review-code-changes/scripts/collect_changes.py --help
python3 review-code-changes/scripts/render_diff.py --help
```

完整工作流、报告格式和准出条件见 [`review-code-changes/SKILL.md`](review-code-changes/SKILL.md)。
