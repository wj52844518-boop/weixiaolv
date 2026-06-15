# CONNECTORS.md — 连接器规范

> 本文档定义 weixiaolv-execution-penalty 与外部系统（案件管理、图谱、通知）的接口契约。
> version: 1.0 | 更新日期: 2026-06-15

---

## 一、架构设计原则

本 Skill 为**原子化独立包**，默认在**无外部依赖**的完全离线状态下运行。
外部系统（案件管理数据库/Neo4j图谱/飞书通知）为**可选增强**，通过标准化接口按需接入。

```
┌─────────────────────────────────────────────────────┐
│           execution-penalty (原子化独立包)            │
│                                                     │
│  输入: case.json 执行状态快照（本地 JSON 文件）        │
│  输出: penalty_report + 文书包（本地文件系统）         │
│                      │                              │
│         ┌────────────┴────────────┐                 │
│         ▼                         ▼                 │
│  【可选】Neo4j 图谱写入    【可选】飞书通知推送        │
│  【可选】案件管理系统      【可选】律师微信通知        │
└─────────────────────────────────────────────────────┘
```

---

## 二、核心输入接口（case.json 快照格式）

```json
{
  "case_id": "ENF_2025_XXX",
  "case_name": "申请执行人李四 vs 被执行人王五",
  "execution_state": {
    "obligation": {
      "has_final_judgment": true,
      "judgment_date": "2023-11-15",
      "judgment_amount": 500000.00,
      "enforcement_notice_sent_date": "2023-12-01"
    },
    "capability": {
      "has_bank_accounts": true,
      "has_real_estate": true,
      "has_vehicles": true,
      "has_high_consumption_records": false
    },
    "violations_detected": [
      {
        "code": "T1",
        "description": "以30万元明显不合理低价转让名下房产给关联人",
        "occurred_date": "2024-01-10",
        "evidence_status": "partial"
      }
    ],
    "police_report": {
      "has_filed": true,
      "filed_date": "2026-05-01",
      "police_receipt_received": true,
      "has_written_response": false,
      "days_since_filed": 45
    },
    "court_status": {
      "is_supportive": true,
      "has_transfer_request": false
    }
  }
}
```

---

## 三、输出接口

### 3.1 刑事追刑战术载荷（penalty_payload）

写入 `case.json` 的 `litigation_details.penalty_payload` 字段，JSON Schema 参见 `assets/penalty_report_schema.json`。

### 3.2 可选：Neo4j 图谱写入

```
# 写入节点类型
PenaltyCase:     刑事追刑案件（案件ID / 追刑路径 / 严重程度）
CriminalAct:     犯罪行为节点（T1/T1.5/T2... 特征码）
EvidenceItem:    证据项节点（complete/partial/missing）

# 写入关系
CASE_OF --[TRIGGERS]--> CriminalAct
CASE_OF --[ASSESSES]--> EvidenceItem
```

当 `NEO4J_URI` 环境变量存在时，自动写入图谱。

### 3.3 可选：飞书通知推送

当 `FEISHU_WEBHOOK_URL` 环境变量存在时，自动推送红色预警卡片到预设群。

---

## 四、环境变量接口

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `NEO4J_URI` | 否 | Neo4j Bolt URI，如 `bolt://localhost:7687` |
| `NEO4J_USER` | 否 | Neo4j 用户名 |
| `NEO4J_PASSWORD` | 否 | Neo4j 密码 |
| `FEISHU_WEBHOOK_URL` | 否 | 飞书群机器人 Webhook URL |
| `CASE_CONTEXT_DIR` | 否 | 案件上下文目录，默认 `./cases` |

---

## 五、免责声明（Legal Disclaimer）

本工具为**法律辅助软件**，不构成律师法律意见，不对案件结果作任何承诺。
使用前请咨询执业律师确认策略适用性。
