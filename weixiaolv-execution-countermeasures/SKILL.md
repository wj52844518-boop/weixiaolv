---
name: execution-countermeasures
description: "当用户提出'债务人转移资产'、'公司换壳逃债'、'虚构债务'、'假离婚避债'、'如何追加股东/关联人'、'追加被执行人'时触发。负责识别逃废债套路，并输出'直接追加'或'另案起诉'的精细化反制方案。"
metadata:
  trigger_keywords:
    - "转移资产"
    - "转移财产"
    - "换壳逃债"
    - "追加被执行人"
    - "追加股东"
    - "恶意避债"
    - "假离婚"
    - "抽逃出资"
    - "违法减资"
    - "违法注销"
  priority: P0
  outputs:
    - "逃废债伎俩识别报告"
    - "28种直接追加可行性评估"
    - "52种诉讼穿透路径设计"
---

# 技能：反逃废债伎俩与追加主体反制 (execution-countermeasures)

> 版本：V1.1 | 更新：2026-06-16（自然人N1-N10路由注入）
> 别名：反制探员（Countermeasure Agent）
> 架构：乐高化子模块（natural_person_auditor.py 为执行引擎核心）

---

## 一、核心职责

**本模块对自然人债务人和法人债务人分别路由至不同的子模块执行**：

| 债务人类型 | 执行子模块 | 路由条件 |
|-----------|-----------|---------|
| **自然人** | `scripts/natural_person_auditor.py`（NaturalPersonAuditor）| 被执行人为自然人，或案件证据材料以自然人逃废债套路为主 |
| **法人** | `references/52_litigation_expansion.md` + `28_direct_expansion.md` | 被执行人为公司/企业主体 |

**自然人路由触发词**（自动识别）：
- 假离婚、离婚析产、假买卖、假赠与、财产代持、虚假诉讼
- 虚构租赁、案外人异议、双户口、多护照、勾兑执行
- "查一下这个自然人是怎么逃债的"、"按逃废债套路逐项审核证据"

**路由决策树**：
```
案件债务人类型 = 自然人？
  → YES：加载 scripts/natural_person_auditor.py
       → NaturalPersonAuditor.run_audit()
       → 输出《自然人逃废债伎俩识别与反制报告》
       → 路由至 countermeasure_matrix.json（natural 系列 tactic_code）
  → NO：加载 28_direct_expansion.md + 52_litigation_expansion.md
       → 按原流程执行法人逃废债反制
```

---

## 一、自然人逃废债N1-N10路由分发（V1.1新增）

### 自然人子模块职责
当执行代理（Execution Agent）识别到被执行人为**自然人**时，自动触发本路由：

1. **证据审查阶段**：调用 `NaturalPersonAuditor.run_audit()`
   - 输入：案件证据材料（用户提供或猎犬座穿透结果）
   - 处理：10类套路 × 6-8个证据项逐项核查
   - 输出：CONFIRMED / SUSPECTED / RULED_OUT 状态 + 证据缺口清单

2. **反制路由阶段**：根据审查结果，加载 `countermeasure_matrix.json`
   - 命中的 tactic_code → 锁定具体法律路径
   - 区分 DIRECT_EXPANSION（执行程序内追加）vs LITIGATION_EXPANSION（另案起诉）

3. **文书生成阶段**：调用 execution-documents（行辕）
   - 三段式对抗说理（RE→RO→RB）直接注入文书事实与理由章节
   - auto_fill.py 一键生成 .docx

### 自然人N1-N10 × 反制路径映射

| 套路 | tactic_code | 反制路由 | 核心法条 |
|------|------------|---------|---------|
| N1 假离婚析产 | TACTIC_NATURAL_DIVORCE | LITIGATION | 民法典§538债权人撤销权 |
| N2 假买卖 | TACTIC_NATURAL_FAKE_SALE | LITIGATION | 民法典§538/539撤销权 |
| N3 假赠与 | TACTIC_NATURAL_FAKE_DONATION | LITIGATION | 民法典§538撤销权 |
| N4 财产代持 | TACTIC_NATURAL_ASSET_HOLDING | LITIGATION | 民法典§209条推翻登记推定 |
| N5 虚假诉讼保护 | TACTIC_NATURAL_FAKE_DEBT_MORTGAGE | LITIGATION + 刑事 | 刑法§307条之一 + 民诉法§59 |
| N6 虚构债务抵押 | TACTIC_NATURAL_FAKE_DEBT_MORTGAGE | LITIGATION | 民法典§538（恶意延长债权）|
| N7 虚构长期租赁 | TACTIC_NATURAL_FAKE_LEASE | LITIGATION | 民法典§725条（攻击占有要件）|
| N8 案外人异议 | TACTIC_NATURAL_FAKE_LEASE | LITIGATION | 执行异议之诉（涤除租赁权）|
| N9 双户口多护照 | TACTIC_NATURAL_DUAL_HOUSEHOLD | DIRECT + LITIGATION | 同人异名证明 + 追加配偶 |
| N10 勾兑干扰执行 | TACTIC_NATURAL_DELAY | 刑事举报 | 刑法§313拒执罪 + §399条举报 |

---

## [原有章节] 一、核心职责（法人部分）

对债务人（自然人或法人）的规避执行、掏空企业、关联变更等逃废债伎俩进行**模式识别（Pattern Recognition）**，并针对性地编排"执行程序内直接追加（28种）"或"另案提起穿透诉讼（52种）"的精细化反制路径。

---

## 二、渐进式执行流（Progressive Process）

### 第一阶段：逃废债套路识别 (Tactic Recognition)

**动作**：
- 从猎犬座（execution-investigation）穿透出的异常关联交易、零对价转让、关键人换壳事实中，提取行为特征
- 与 `references/evasion_tactics.md` 做模式碰撞

**加载资源**：`references/evasion_tactics.md`

**输出**：`identified_evasion_tactic`（如：恶意低价转让资产、一人公司混同、金蝉脱壳）

---

### 第二阶段：法律路径路由 (Countermeasure Routing)

**触发条件**：成功锁定 `identified_evasion_tactic`

**加载资源**：`assets/countermeasure_matrix.json`

**动作**：
- 在 `tactic_mappings[]` 中检索匹配的 `tactic_code`
- 判定 `route_type` ∈ {"DIRECT_EXPANSION", "LITIGATION_EXPANSION"}
- 参考 `priority_rules` 中的 P0_MUST_TRY_DIRECT_FIRST / P1_DUAL_TRACK

**输出**：`target_route_type`

---

### 第三阶段：精细化法理与证据对齐 (Fine-grained Analysis)

**触发条件**：获取 `target_route_type`

**加载资源**：
- 若为 `DIRECT_EXPANSION` → `references/28_direct_expansion.md`
- 若为 `LITIGATION_EXPANSION` → `references/52_litigation_expansion.md`

**动作**：
- 锁定具体追加路径（如追加出资不实股东 → 追加规定第17条）
- 评估证据完整度
- 将缺失证据推送至 GapFiller 引擎

**输出**：`execution_countermeasure_plan`（反制作战计划）

---

## 三、核心映射资产

### assets/countermeasure_matrix.json

13 个高频逃废债伎俩 × 法律反制路径映射：

| tactic_code | 伎俩 | 路由 | 反制路径 |
|------------|------|------|---------|
| TACTIC_NATURAL_DIVORCE | 假离婚析产 | LITIGATION | 债权人撤销权之诉§538 |
| TACTIC_CORP_SHELL_TRANSFER | 资产虚假转移 | LITIGATION | 债权人撤销权之诉§538/539 |
| TACTIC_SHAREHOLDER_UNPAID_CAPITAL | 未出资股东 | DIRECT + LITIGATION | 追加规定§17 + 追缴出资纠纷 |
| TACTIC_SHAREHOLDER逃亡HIDING | 抽逃出资 | DIRECT + LITIGATION | 追加规定§18 + 追收抽逃出资 |
| TACTIC_CORP_SHELL_SWAP | 金蝉脱壳 | LITIGATION | 横向人格否认§23 |
| TACTIC_CORP_ILLEGAL_REDUCTION | 违法减资 | LITIGATION | 股东损害赔偿§226 |
| TACTIC_CORP_ILLEGAL_LIQUIDATION | 违法注销 | DIRECT + LITIGATION | 追加规定§21 + 清算责任纠纷 |
| TACTIC_ONE_PERSON_COMPANY_MINGLING | 一人公司混同 | DIRECT + LITIGATION | 追加规定§20 + 股东连带责任 |
| TACTIC_NATURAL_FAKE_LEASE | 虚构长期租赁 | LITIGATION | 执行异议之诉（排除租赁） |
| TACTIC_CORP_DEFAMT_HIDING | 资金挂他人名下 | LITIGATION | 纵向人格否认§23 |
| TACTIC_CORP_NAME_ADDR_CHANGE | 换壳+改法定代表人 | DIRECT + LITIGATION | 追加规定§20 + 过度支配控制 |
| TACTIC_NATURAL_DUAL_HOUSEHOLD | 双户口多护照 | LITIGATION | 追加配偶财产+律师调查令 |
| TACTIC_CORP_CLONING | 克隆冒名 | LITIGATION | 横向人格否认§23 |

---

## 四、与双子星乐高库的联动

```
execution-investigation（猎犬座）
    ↓ 发现：王五将龙腾盛世60%股权以0元转让给小舅子
    ↓ 触发 TRIG_D1（判决后转移财产）
    ↓ 标记：TACTIC_CORP_SHELL_TRANSFER

execution-countermeasures（本技能）
    ↓ 加载 countermeasure_matrix.json
    ↓ 路由：LITIGATION_EXPANSION
    ↓ 锁定：债权人撤销权之诉（民法典§538/539）
    ↓ 输出：execution_countermeasure_plan

execution-litigation（军师座）
    ↓ 加载 COA_012（债权人撤销权）
    ↓ 四象限矩阵 + 证明责任移转
    ↓ 输出：adjusted_adversarial_matrix

execution-documents（行辕）
    ↓ 三段式渲染 + auto_fill
    ↓ verify_doc 9项核验
    ↓ 最终清洁 .docx 文书 ✅
```

---

## 五、文件结构

```
skills/execution-countermeasures/
├── SKILL.md                              ← 本文件（三阶段渐进式SOP + metadata）
├── references/
│   ├── evasion_tactics.md                ← 伎俩库：自然人10套路+法人13套路特征码
│   ├── 28_direct_expansion.md            ← 行动库：执行程序内直接追加（28种）
│   ├── 52_litigation_expansion.md        ← 诉讼库：另行起诉穿透追加（52种）
│   └── execution_methodology.md          ← 心法库：四方针 + 律师三查 + 九大动作
└── assets/
    └── countermeasure_matrix.json        ← 矩阵：伎俩特征 → 法律反制路径映射表
```

---

## 六、版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-06-13 | 乐高化重构版：从 3000 行执行流程方案.md 拆解为4个 progressive 子文档 + 1个路由矩阵 |

---

*本 Skill 为韦小律 V6.x+10 三星联动战术层 | P0 强制路由协议*