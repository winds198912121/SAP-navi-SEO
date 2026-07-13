# JP Recruit Extractor — 日本招聘案件データ抽出システム

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-purple)](.claude/skills/run-jp-recruit-extractor/)

**AI 引导 → 规则固化 → 逐步脱离 LLM** 的日本 IT 招聘案件智能数据提取系统。

---

## 📦 一键安装为 Claude Code Skill

任何人都可以通过以下命令将此项目安装为全局 Skill，在任何 Claude Code 会话中调用：

```bash
curl -fsSL https://github.com/winds198912121/SAP-navi-SEO/jp-recruit-extractor/main/scripts/install-skill.sh | bash
```

安装后，在 Claude Code 中直接说：
> **"帮我运行 jp-recruit-extractor"**

或在项目目录内使用自定义命令：

| 命令 | 用途 |
|------|------|
| `/extract` | 规则提取（0.3 秒，LLM 不用） |
| `/evaluate` | 品质评估 |
| `/export` | Excel 输出 |
| `/status` | 项目状态 |
| `/rule` | 规则统计 / 搜索 |

---

## 概要

日本 IT 招聘市场每天流通大量案件资料（PDF / Word / Excel / HTML / 邮件 / 图片），格式繁杂。本项目通过 **LLM 提取 → 自动学习规则 → 规则引擎为主、LLM 兜底** 的三步走策略，实现：

- **Phase 1**: 纯 LLM 模式，快速上线，准确率 ≥ 90%
- **Phase 2**: 规则学习引擎自动从 LLM 结果中归纳提取规则
- **Phase 3**: 80%+ 案件无需 LLM，秒级规则提取，准确率 ≥ 95%
- **Phase 4**: 规则库持续进化，维护成本趋近于零

## 快速开始

```bash
# 1. 安装
git clone https://github.com/winds198912121/SAP-navi-SEO//jp-recruit-extractor.git
cd jp-recruit-extractor
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. 规则提取（LLM 不用，0.3 秒）
python3 src/run_pipeline.py && python3 src/export_excel.py

# 3. 或启动交互式反馈循环（推荐）
python3 src/interactive_feedback.py
```

输出:
- JSON: `data/output/extraction_result_{timestamp}.json`
- Excel: `data/output/jp_recruit_cases_{timestamp}.xlsx`（41 列）

## 当前品质指标 (2026-07-05 实測)

| 指标 | 值 |
|------|-----|
| 规则库 | **107** 规则 / 11 字段 |
| 总案件数 | **28 件**（3 文件） |
| 案件名提取率 | **100%** |
| 技能提取率 | **96%** |
| 期间提取率 | **96%** |
| 案件全文保持率 | **100%** |
| 处理时间 | ~0.3 秒（0 元） |

## 作为 Claude Code Skill 使用

### 方法 A：全局注册（一次安装到处用）

```bash
bash scripts/install-skill.sh
```

之后在任何 Claude Code 会话中可调用 `/run-jp-recruit-extractor` Skill。

### 方法 B：项目内使用

clone 后在项目根目录运行 Claude Code 即可自动识别 `.claude/skills/` 和 `.claude/commands/`。

### Skill 内容

```
.claude/skills/run-jp-recruit-extractor/
├── SKILL.md          # 完整 Skill 定义
└── driver.sh         # 冒烟测试驱动

.claude/commands/
├── extract.md        # /extract — 规则提取
├── llm-extract.md    # /llm-extract — LLM 提取
├── evaluate.md       # /evaluate — 品质评估
├── export.md         # /export — Excel 输出
├── status.md         # /status — 状态确认
├── rule.md           # /rule — 规则管理
├── learn-rules.md    # /learn-rules — 规则学习
├── add-data.md       # /add-data — 数据追加
└── init.md           # /init — 项目初始化
```

## 目录结构

```
jp-recruit-extractor/
├── README.md
├── requirements.txt
├── setup.py
├── scripts/
│   └── install-skill.sh            # ★ 一键 Skill 安装脚本
│
├── .claude/
│   ├── CLAUDE.md                   # Claude Code 项目文档
│   ├── skills/run-jp-recruit-extractor/  # Skill 定义
│   │   ├── SKILL.md
│   │   └── driver.sh
│   └── commands/                   # 9 个自定义命令
│
├── docs/                           # 文档
│   ├── 01-field-definition.md     # 字段定义规范
│   ├── 02-rule-format-spec.md     # 规则格式规范
│   ├── 03-system-architecture.md  # 系统架构设计
│   ├── 04-prompt-templates/       # LLM Prompt 模板集
│   ├── 05-user-manual.md          # 用户操作手册
│   ├── 06-rule-development-guide.md  # 规则开发指南
│   ├── 07-format-onboarding.md    # 新格式适配流程
│   └── 08-api-docs.md             # API 文档
│
├── src/                           # 源代码
│   ├── run_pipeline.py            # 规则提取管线（核心）
│   ├── interactive_feedback.py    # ★ 交互反馈循环
│   ├── llm_fix.py                 # LLM 分析模块
│   ├── rule_writer.py             # 规则自动生成
│   ├── export_excel.py            # Excel 输出
│   ├── run_llm_pipeline.py        # DeepSeek LLM 管线
│   ├── merge_results.py           # 结果合并
│   ├── cli.py                     # CLI 入口
│   ├── config.py                  # 全局配置
│   ├── common/                    # 数据模型 & 工具
│   ├── rule_engine/               # 规则引擎
│   ├── rule_learner/              # 规则学习引擎
│   ├── rule_repository/           # 规则存储
│   ├── llm_engine/                # LLM 客户端
│   ├── preprocessor/              # 文档预处理
│   └── api/                       # FastAPI 服务
│
├── data/                          # 数据目录
│   ├── rules/field_rules.json     # 规则库 (107 规则)
│   ├── output/                    # 提取结果
│   ├── 案件1.txt                  # 样本数据
│   ├── 案件List.md
│   └── 7月SAP案件一覧_0610.xlsx
│
└── tests/                         # 测试
```

## 核心理念

```
输入文件 (PDF/Word/Excel/HTML/邮件/图片)
    │
    ▼
预处理层 ─→ 格式归一化 / 文本提取 / 日语标准化
    │
    ▼
路由调度层 ─→ 规则匹配检查 → 决策: 规则 | LLM | 混合
    │
    ▼
提取执行层 ─→ 规则引擎 / LLM 引擎 → 结果融合
    │
    ▼
后处理验证层 ─→ 字段校验 / 标准化 / 冲突检测
    │
    ▼
输出 JSON
```

## 开发路线

| 阶段 | 时间 | 产出 |
|---|---|---|
| Phase 0: 探索定义 | Week 1-2 | 字段定义、样本收集、PoC |
| Phase 1: LLM 管线 | Week 3-5 | 端到端 LLM 提取 |
| Phase 2: 规则学习 | Week 6-9 | 规则引擎 + 学习引擎 |
| Phase 3: 规则丰富 | Week 10-13 | 覆盖 80%+ 案件 |
| Phase 4: 持续优化 | ongoing | 全自动闭环 |

## License

MIT

---

*Built for Japanese IT recruitment market — 日本 IT 招聘案件のためのデータ抽出ツール*
