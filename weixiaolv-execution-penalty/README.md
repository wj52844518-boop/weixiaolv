# 韦小律·拒执罪刑事自诉与追刑 Agent 插件

# Weixiaolv – CN Execution Evasion Criminal Prosecution Assistant

[![Project Status: Active](https://img.shields.io/badge/Status-Active-brightgreen)](#)
[![Legal Basis: 2024解释+2025意见](https://img.shields.io/badge/Legal%20Basis-法释〔2024〕13号+法发〔2025〕8号-blue)](#)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9+-blue)](#)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-green)](#)

> ⚠️ **强制执行不仅是财产查控，更是一场「以刑促执」的立体战役。**
> **Enforcement is not merely asset seizure—it's a multi-dimensional campaign of "using criminal prosecution to compel execution."**

---

## 中文版 | 中文说明

### 📋 项目概述

本插件是基于 **OpenClaw Agent 架构规范** 独立封装的中国法律执行实战 Skill 包。旨在辅助中国民商事律师与执行案外人，通过严密的程序决策树和证据链映射，将老赖的逃债行为精准转化为刑事拘留与自诉控告。

**这是一把刺向法律科技市场的「特种钢刀」——体积小、精度高、杀伤力极大。**

---

### 🔐 核心法理与最新司法解释刚性对齐

#### 2024年12月1日施行：法释〔2024〕13号

《最高人民法院、最高人民检察院关于办理拒不执行判决、裁定刑事案件适用法律若干问题的解释》

- ✅ **T1.5 黄金窗口**（最大亮点）：犯罪时间前移至「判决生效前」——诉前/诉中转移财产 → 可追溯为拒执罪
- ✅ 十大「情节严重」特征码自动检测（T1–T8 + TS1–TS3 情节特别严重）
- ✅ 主体范围扩展：实际控制人/控股股东可被直接追诉（§2）

#### 2025年7月1日施行：法发〔2025〕8号

《最高人民法院、最高人民检察院、公安部关于办理拒不执行判决、裁定刑事案件若干问题的意见》

- ✅ **「30天自诉前置窗口」自动计算**（EMS寄出日 = 起算日，第31天一键解锁自诉）
- ✅ 公诉转自诉法定决策树（第15-18条）：三选一前置条件自动核验
- ✅ 证据链健康度按刑事「排除合理怀疑」标准评估

---

### 🧠 三引擎联动架构

```
[输入：case.json 执行状态快照]
    │
    ▼
【引擎一：trigger_checker.py】
  检测「情节严重」特征码（T1–T8 + TS1–TS3）
  → matched_triggers[] + prosecution_ready
    │
    ▼ prosecution_ready == true
【引擎二：route_selector.py】
  确定合法追刑路径（2025意见第15-18条）
  → route ∈ {NONE / COURT_PUBLIC_TRANSFER / PUBLIC_REPORT_FIRST / PRIVATE_PROSECUTION}
    │
    ▼
【引擎三：evidence_mapper.py】
  刑事「排除合理怀疑」标准评估证据链
  → chain_health + gaps[] + investigation_applications[]
    │
    ▼
【文书装配】
  PRIVATE_PROSECUTION → 刑事自诉状.docx
  PUBLIC_REPORT_FIRST → 刑事控告书.docx
  COURT_PUBLIC_TRANSFER → 移送申请书.docx
```

---

### 🚀 快速开始

#### 方法一：Git Clone（推荐 / Recommended）

```bash
# 克隆至 Claude Desktop 工作区
git clone https://github.com/openclaw/weixiaolv-execution-penalty.git \
  ~/.openclaw/skills/weixiaolv-execution-penalty
```

#### 方法二：手动下载

1. 下载本仓库 ZIP 包
2. 解压至 `~/.openclaw/skills/weixiaolv-execution-penalty/`

#### 使用方式（Claude Desktop / Cursor / Windsurf）

```
用户：请分析李四诉王五拒执罪可行性
      王五在判决生效后将其奔驰车（评估价50万）以3万元过户给其小舅子，
      我于35天前向当地公安局邮寄了刑事控告书，至今未收到任何书面答复。

Agent 响应：
  → 自动调用 trigger_checker.py   → T1（明显不合理价格转让财产）命中
  → 自动调用 route_selector.py   → PRIVATE_PROSECUTION（公安30天超期）
  → 自动调用 evidence_mapper.py → 证据链健康度 72%
  → 自动装配《拒不执行判决裁定罪刑事自诉状.docx》
```

---

### 📁 仓库结构

```
weixiaolv-execution-penalty/
├── .claude-plugin/
│   ├── plugin.json          ← 插件元数据声明
│   └── marketplace.json    ← Anthropic Marketplace 索引
├── SKILL.md                ← 核心 SOP + 三引擎联动规范
├── CONNECTORS.md           ← 可选连接器接口（Neo4j/飞书）
├── scripts/
│   ├── trigger_checker.py   ← 引擎一：情节严重特征码检测
│   ├── route_selector.py    ← 引擎二：追刑路径决策树
│   ├── evidence_mapper.py   ← 引擎三：刑事证据链映射
│   └── generate_penalty_doc.py ← 文书生成渲染引擎
├── references/
│   ├── 2024_judicial_interpretation.md  ← 法释〔2024〕13号原文+解读
│   ├── 2025_joint_opinion.md            ← 法发〔2025〕8号原文+程序图
│   └── gotchas.md                       ← 10个高频踩坑点
└── assets/
    ├── penalty_report_schema.json       ← 刑事追刑战术载荷 JSON Schema
    └── templates/                        ← 三套刑事文书 Word 模板
```

---

### 📜 十大情节严重特征码速查

| 代码 | 情形 | 证据要点 |
|------|------|---------|
| T1 | 隐藏/转移/低价转让财产 | 过户协议+银行流水 |
| **T1.5** ⭐ | **判决生效前即开始转移财产** | 过户时间 vs 判决生效时间对比 |
| T2 | 虚假诉讼/仲裁/调解 | 串通证据+诉讼材料时间线 |
| T3 | 拒不交出可供执行财产 | 搜查记录+拒交证据 |
| T4 | 司法拘留后仍不执行 | 拘留决定书+拘留后仍不履行 |
| T5 | 违反限高经罚款后仍高消费 | 限高令送达回证+消费记录 |
| T6 | 虚假报告/伪造财产证据 | 虚假申报表+伪造材料 |
| T7 | 转移共有财产/赠与 | 过户记录+亲属关系证明 |
| T8 | 其他情节严重 | 综合证据 |
| TS1-3 | **情节特别严重（3-7年）** | 个人≥100万/单位≥500万 |

---

### ⚖️ 追刑路径速查

| 路径 | 适用情形 | 前置条件 | 文书 |
|------|---------|---------|------|
| **A：刑事自诉** | 公安30天超期 / 不予立案 / 检察院不起诉 | 三选一 | 刑事自诉状 |
| **B：法院移送公安** | 执行法院配合度高 | 无 | 移送申请书 |
| **C：公安控告（起步）| 任何情形 | 无 | 刑事控告书 |

---

### 🔧 配置（可选）

```bash
# Neo4j 图谱写入（可选）
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password

# 飞书通知推送（可选）
export FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

---

### 📦 依赖

```
Python >= 3.9
标准库：dataclasses, enum, datetime, typing
无外部强制依赖（完全离线可运行）
```

---

### ⚠️ 免责声明

本插件为法律辅助工具，不构成律师法律意见，不对案件结果作任何承诺。
使用前请咨询执业律师确认策略适用性。所有法律风险由使用者自行承担。

---

## English Version

### 📋 Overview

**weixiaolv-execution-penalty** is a standalone, production-ready Claude Agent Skill for Chinese criminal enforcement litigation. It provides Chinese civil/commercial lawyers with an automated decision pipeline to pursue criminal charges against debtors who evade court-ordered execution obligations.

**This is the world's first open-source AI tool dedicated to China's "拒执罪" (Execution Evasion Criminal Act, Criminal Law §313).**

---

### 🔐 Legal Basis (2024解释 + 2025意见)

**法释〔2024〕13号** (Effective 2024-12-01):
- **T1.5 Time-window Expansion** (Most Impactful): Criminal liability now attaches even when assets are transferred *before* the judgment becomes final—revolutionary for pre-litigation asset concealment cases.
- 10 "Serious Circumstances" trigger codes + 3 "Especially Serious" codes.
- Subject scope expanded to include *de facto controllers* and controlling shareholders.

**法发〔2025〕8号** (Effective 2025-07-01):
- **30-Day Self-Prosecution Window**: Auto-calculated from EMS dispatch date. Day 31 unlocks direct criminal self-prosecution.
- Mandatory prerequisite tree: police non-registration / 30-day silence / procuratorate non-prosecution (any one triggers self-prosecution right).
- Criminal evidence standard ("排除合理怀疑" / beyond reasonable doubt) enforced throughout.

---

### 🧠 Three-Engine Architecture

| Engine | Script | Function |
|--------|--------|----------|
| **Engine 1** | `trigger_checker.py` | Detects "serious circumstances" trigger codes (T1–T8 + TS1–TS3) |
| **Engine 2** | `route_selector.py` | Selects prosecution path per 2025 Opinion Articles 15–18 |
| **Engine 3** | `evidence_mapper.py` | Maps evidence chain to "beyond reasonable doubt" standard |

---

### 🚀 Quick Start

```bash
# Clone to your Claude Desktop workspace
git clone https://github.com/openclaw/weixiaolv-execution-penalty.git \
  ~/.openclaw/skills/weixiaolv-execution-penalty
```

Then in your Claude Desktop / Cursor / Windsurf chat:

```
User: Analyze whether we can pursue criminal prosecution against Wang Wu
      (debtor transferred a Mercedes worth 500k to his brother-in-law for 30k
       after judgment became final, and police have given no written response
       in 35 days since our EMS criminal complaint).

Agent: → trigger_checker.py: T1 (unreasonably low price transfer) HIT
        → route_selector.py: PRIVATE_PROSECUTION (police 30-day silence)
        → evidence_mapper.py: Evidence chain health 72%
        → Auto-generates: Criminal Self-Prosecution Indictment (.docx)
```

---

### 📄 Templates Included

| Document | Path | Route |
|----------|------|-------|
| 拒不执行判决裁定罪刑事自诉状 | `templates/` | Route A (Self-Prosecution) |
| 刑事控告书（公安机关报案用）| `templates/` | Route C (Police Report) |
| 移送公安机关立案侦查申请书 | `templates/` | Route B (Court Referral) |

---

### 🤝 Contributing

Issues and pull requests welcome. For legal-specific questions or case studies, open a Discussion.

---

### 📜 License

Apache License 2.0

---

### 🙏 Acknowledgments

Developed by **OpenClaw 韦小律 Team**.
Powered by **OpenClaw Agent Architecture**.
Legal foundation: 刑法§313 · 法释〔2024〕13号 · 法发〔2025〕8号.

*Built in China, for Chinese lawyers.*
