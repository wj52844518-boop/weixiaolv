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
    - "违法破产"
    - "强制吊销"
    - "脱壳"
    - "克隆公司"
    - "逃废债"
  priority: P0
  outputs:
    - "逃废债伎俩识别报告"
    - "28种直接追加可行性评估"
    - "52种诉讼穿透路径设计"
---

# 技能：反逃废债伎俩与追加主体反制 (execution-countermeasures)

> 版本：V2.0 | 更新：2026-06-16（自然人N1-N10 + 法人C1-C17全量接入）
> 别名：反制探员（Countermeasure Agent）
> 架构：乐高化双子引擎（natural_person_auditor.py + legal_entity_auditor.py）

---

## 一、核心职责

**本模块对自然人债务人和法人债务人分别路由至不同的子模块执行**：

| 债务人类型 | 执行引擎 | 套路数量 | 路由触发条件 |
|-----------|---------|---------|------------|
| **自然人** | `scripts/natural_person_auditor.py` | N1-N10（10类）| 被执行人为自然人 |
| **法人** | `scripts/legal_entity_auditor.py` | C1-C17（17类）| 被执行人为公司/企业 |

**触发词**（自动识别债务人类型并路由）：
- 自然人触发词：假离婚、离婚析产、假买卖、假赠与、财产代持、虚假诉讼、虚构租赁、双户口、多护照、勾兑执行
- 法人触发词：脱壳、金蝉脱壳、克隆公司、违法减资、违法清算、违法注销、强制吊销、违法破产、更改公司名称、更换法定代表人、资金代持、资产虚假转移、虚构抵押

**路由决策树**：
```
用户输入 → 识别债务人类型
  → 自然人：NaturalPersonAuditor.run_audit() → 《自然人报告》→ countermeasure_matrix.json
  → 法人：  LegalEntityAuditor.run_audit()  → 《营利法人报告》 → countermeasure_matrix.json
  → 路由至具体法律路径（DIRECT_EXPANSION 或 LITIGATION_EXPANSION）
  → execution-documents：RE→RO→RB三段式注入文书
```

---

## 二、自然人逃废债 N1-N10（子模块：natural_person_auditor.py）

### 套路 × 反制路径映射

| 套路 | tactic_code | 路由 | 核心法条 |
|------|------------|------|---------|
| N1 假离婚析产 | TACTIC_NATURAL_DIVORCE | LITIGATION | 民法典§538债权人撤销权 |
| N2 假买卖 | TACTIC_NATURAL_FAKE_SALE | LITIGATION | 民法典§538/539撤销权 |
| N3 假赠与 | TACTIC_NATURAL_FAKE_DONATION | LITIGATION | 民法典§538撤销权 |
| N4 财产代持 | TACTIC_NATURAL_ASSET_HOLDING | LITIGATION | 民法典§209条推翻登记推定 |
| N5 虚假诉讼保护 | TACTIC_NATURAL_FAKE_DEBT_MORTGAGE | LITIGATION+刑事 | 刑法§307条之一+民诉法§59 |
| N6 虚构债务抵押 | TACTIC_NATURAL_FAKE_DEBT_MORTGAGE | LITIGATION | 民法典§538（恶意延长债权）|
| N7 虚构长期租赁 | TACTIC_NATURAL_FAKE_LEASE | LITIGATION | 民法典§725条（攻击占有要件）|
| N8 案外人异议 | TACTIC_NATURAL_FAKE_LEASE | LITIGATION | 执行异议之诉（涤除租赁权）|
| N9 双户口多护照 | TACTIC_NATURAL_DUAL_HOUSEHOLD | DIRECT+LITIGATION | 同人异名证明+追加配偶 |
| N10 勾兑干扰执行 | TACTIC_NATURAL_DELAY | 刑事举报 | 刑法§313拒执罪+§399条举报 |

### N1/N4/N9 杀手锏证据规格

| 套路 | 杀手锏证据 | 穿透强度 |
|------|----------|---------|
| N1 假离婚 | 离婚后债务人账户仍支付物业水电费+银行流水显示资金转配偶 | ⭐⭐⭐⭐ |
| N4 代持 | 实际出资银行流水（债务人账户直接打款给开发商/卖家） | ⭐⭐⭐⭐⭐ |
| N9 双户口 | 公安机关《同人异名证明》 | ⭐⭐⭐⭐⭐ |

---

## 三、营利法人逃废债 C1-C17（子模块：legal_entity_auditor.py）⭐V2.0新增

### 套路 × 反制路径映射

| 套路 | tactic_code | 路由 | 核心法条 |
|------|------------|------|---------|
| C1 资产虚假转移 | TACTIC_CORP_SHELL_TRANSFER | LITIGATION | 民法典§538/539撤销权 |
| C2 财产代持 | TACTIC_CORP_FUND_HIDING | LITIGATION | 新公司法§23纵向人格否认 |
| C3 自有财产不办凭证 | TACTIC_CORP_FUND_HIDING | LITIGATION | 民法典§209条推翻登记推定 |
| C4 虚假诉讼保护 | TACTIC_CORP_SHELL_TRANSFER | LITIGATION+刑事 | 刑法§307条之一虚假诉讼罪 |
| C5 虚构债务抵押 | TACTIC_CORP_SHELL_TRANSFER | LITIGATION | 民法典§538撤销担保物权 |
| C6 虚构长期租赁 | TACTIC_CORP_SHELL_TRANSFER | LITIGATION | 民法典§725条攻击占有要件 |
| C7 案外人异议阻挡 | TACTIC_CORP_SHELL_TRANSFER | LITIGATION | 执行异议之诉（涤除权）|
| C8 脱壳（金蝉脱壳）| TACTIC_CORP_SHELL_SWAP | LITIGATION | 新公司法§23横向人格否认 |
| C9 资金放他人名下 | TACTIC_CORP_DEFAMT_HIDING | LITIGATION | 新公司法§23纵向人格否认 |
| C10 更改名称/地址 | TACTIC_CORP_NAME_ADDR_CHANGE | DIRECT+LITIGATION | 追加规定§20+过度支配控制 |
| C11 更换法定代表人 | TACTIC_CORP_NAME_ADDR_CHANGE | DIRECT+LITIGATION | 追加规定§17/20+实际控制人追责 |
| C12 克隆（冒名登记）| TACTIC_CORP_CLONING | LITIGATION | 新公司法§23横向人格否认 |
| C13 违法减资 | TACTIC_CORP_ILLEGAL_REDUCTION | LITIGATION | 新公司法§226股东补充赔偿 |
| C14 违法清算/注销 | TACTIC_CORP_ILLEGAL_LIQUIDATION | DIRECT+LITIGATION | 追加规定§21+公司法解释二§20 |
| C15 强制吊销 | TACTIC_CORP_FORCED_REVOCATION | DIRECT+LITIGATION | 公司法解释二§18强制清算+追责 |
| C16 违法破产 | TACTIC_CORP_ILLEGAL_BANKRUPTCY | LITIGATION | 破产法§32撤销+§40追回+§128赔偿 |
| C17 其他逃废债行为 | TACTIC_CORP_OTHER_EVASION | LITIGATION | 刑法§313拒执罪+民诉法§114/248 |

### C8 脱壳 · 三维举证要点

| 举证维度 | 核心证据 |
|---------|---------|
| 人员混同 | 股东/高管在两家公司重叠任职+社保缴纳记录 |
| 业务混同 | 核心合同转至新公司+客户跟随转移+原公司无营收 |
| 财务混同 | 原公司银行流水显示资金转入新公司后立即转出 |

### C13 违法减资 · 撤销权构成

| 要件 | 内容 |
|------|------|
| 时间要件 | 减资发生在债务形成后/诉讼期间/执行期间 |
| 通知要件 | 仅公告未逐一通知已知债权人（违法） |
| 资金要件 | 减资款项退回股东账户后无法说明用途 |

### C16 违法破产 · 三大撤销权

| 撤销权类型 | 法条依据 | 适用场景 |
|-----------|---------|---------|
| 偏颇清偿撤销权 | 破产法第32条 | 破产前1年内对个别债权人清偿 |
| 追回权 | 破产法第40条 | 破产前转移的财产（无偿/低价/个别清偿）|
| 损害赔偿权 | 破产法第128条 | 债务人/高管恶意转移财产损害债权人 |

---

## 四、反制矩阵 countermeasure_matrix.json

16个 tactic_code × 路由类型 × 反制路径：

| tactic_code | 路由 | 行动名称 |
|------------|------|---------|
| TACTIC_CORP_SHELL_TRANSFER | LITIGATION | 债权人撤销权之诉§538/539 |
| TACTIC_CORP_FUND_HIDING | LITIGATION | 纵向人格否认§23 + 审计穿透 |
| TACTIC_CORP_SHELL_SWAP | LITIGATION | 横向人格否认§23（金蝉脱壳）|
| TACTIC_CORP_DEFAMT_HIDING | LITIGATION | 纵向人格否认§23 |
| TACTIC_CORP_NAME_ADDR_CHANGE | DIRECT+LITIGATION | 追加原股东/法定代表人§20 |
| TACTIC_CORP_CLONING | LITIGATION | 横向人格否认§23 |
| TACTIC_CORP_ILLEGAL_REDUCTION | LITIGATION | 股东减资范围内补充赔偿§226 |
| TACTIC_CORP_ILLEGAL_LIQUIDATION | DIRECT+LITIGATION | 追加股东§21+清算责任纠纷 |
| TACTIC_CORP_FORCED_REVOCATION | DIRECT+LITIGATION | 强制清算§18+股东连带责任 |
| TACTIC_CORP_ILLEGAL_BANKRUPTCY | LITIGATION | 破产撤销§32+追回§40+赔偿§128 |
| TACTIC_CORP_OTHER_EVASION | LITIGATION | 拒执罪§313+限高/拘留措施 |
| TACTIC_SHAREHOLDER_UNPAID_CAPITAL | DIRECT+LITIGATION | 追加未出资股东§17 |
| TACTIC_SHAREHOLDER逃亡HIDING | DIRECT+LITIGATION | 追加抽逃出资股东§18 |
| TACTIC_ONE_PERSON_COMPANY_MINGLING | DIRECT+LITIGATION | 追加一人公司股东§20（举证责任倒置）|

---

## 五、文件结构

```
skills/execution-countermeasures/
├── SKILL.md                               ← V2.0 总控（含双子引擎路由）
├── assets/
│   └── countermeasure_matrix.json          ← 16个tactic_code × 法律反制路径
├── references/
│   ├── evasion_tactics.md                 ← V2.0：N1-N10 + C1-C17证据规格
│   ├── 28_direct_expansion.md             ← 执行程序内直接追加（28种）
│   ├── 52_litigation_expansion.md         ← 另案起诉穿透追加（52种）
│   └── execution_methodology.md           ← 心法库
└── scripts/
    ├── natural_person_auditor.py           ← 自然人审计引擎（10类套路）
    └── legal_entity_auditor.py             ← 法人审计引擎（17类套路）⭐V2.0
```

---

## 六、版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-06-13 | 乐高化重构：4个子文档+路由矩阵 |
| V1.1 | 2026-06-16 | N1-N10自然人路由接入 |
| V2.0 | 2026-06-16 | C1-C17法人路由接入（脱壳/克隆/违法减资/强制吊销/违法破产/其他全量） |

---

*本 Skill 为韦小律 V8.x 三星联动战术层 | P0 强制路由协议*
