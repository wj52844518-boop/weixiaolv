# 执行特种战术深度手册：四合一无死角作战

> 韦小律 V7.0 执行特种战术扩展 | 覆盖4大死穴 | 直接可执行

---

## 战术一：唯一住房强制执行穿透模型（EXEC_SOLE_HOUSING）

### 实务痛点

"唯一住房"是老赖最常用的挡箭牌。《执行异议和复议规定》第20条为此提供了明确的执行路径，但实务中律师往往不知道如何操作，导致法官"怕麻烦、怕违规"而不处置。

### 法律依据

| 层级 | 依据 | 内容 |
|------|------|------|
| 司法解释 | 《办理执行异议和复议案件规定》第20条 | 唯一住房可执行的3种情形 |
| 司法解释 | 《最高人民法院关于人民法院办理执行案件若干期限的规定》 | 拍卖/变卖期限要求 |
| 实务规则 | 多省高院执行局解答 | "唯一住房"认定标准+安置费计算规则 |

### 触发条件

```
触发条件（同时满足）：
  ① 查封资产类型 = 住宅（不动产权证载明用途为"住宅"或"公寓"）
  ② 被执行人主张"唯一住房"抗辩
  ③ 标的物评估价值 > 当地廉租房保障面积 × 150%（约54㎡ × 当地均价1.5倍）
     OR 被执行人债务发生后有房产转让记录
```

### 两维度评估模型

#### 维度A：超标的判定（豪宅/大户型）

```python
def evaluate_oversized_housing(area_sqm, local_avg_price, property_value):
    """
    判定是否构成"超标的"住房（可直接执行）
    廉租房保障面积：36㎡（全国标准）× 1.5倍 = 54㎡ 基准
    """
    if area_sqm > 54:
        # 超过54㎡即有可能被认定为"超标准"，但需结合当地房价
        oversized_ratio = area_sqm / 54.0
        return {
            "oversized": True,
            "excess_area": area_sqm - 54,
            "安置费扣除预案": f"按当地市场租金 × {int(oversized_ratio * 5)}年 扣除安置费"
        }
    if property_value > local_avg_price * 1.5:
        # 单价超过当地均价150%
        return {
            "oversized": True,
            "premium_ratio": property_value / (local_avg_price * 1.5),
            "explanation": "单价超过当地均价150%，构成豪宅，可执行"
        }
    return {"oversized": False}
```

#### 维度B：恶意规避判定（债务发生后转让房产）

```python
def evaluate_malicious_evasion(ownership_timeline, debt_occurred_date):
    """
    债务发生后转让房产 → 推定为恶意规避
    依据：《民法典》第538条（债权人撤销权）
    """
    for transfer in ownership_timeline:
        if transfer["type"] == "转让" and transfer["date"] > debt_occurred_date:
            return {
                "malicious": True,
                "transfer_date": transfer["date"],
                "property_address": transfer["address"],
                "recommended_action": "债权人撤销权之诉 + 申请查封该房产"
            }
    return {"malicious": False}
```

### 处置流程

```
【被执行人主张唯一住房】
    ↓
【启动两维度评估】
    ├─ 维度A（超标的）→ 是 → 进入快速执行通道
    └─ 维度B（恶意规避）→ 是 → 触发债权人撤销权 + 撤销原转让房产
    ↓
【生成安置费预案】
    变价款优先扣除：当地市场月租金 × 60个月（5年）/ 96个月（8年）
    余额用于清偿债务
    ↓
【执行法官可直接操作】
    └─ 《唯一住房强制执行申请书及安置过渡预案》→ 一键生成
```

### 输出交付物

**文书编号：文书91（新增）**
- 《唯一住房强制执行申请书及安置过渡（五至八年租金扣除）预案》
- 附件：当地租金评估报告（从贝壳/链家获取区域租金数据）

### 关键话术（律师直接可用）

> "依据《执行异议和复议规定》第20条第1款第（三）项，被执行人名下虽只有一套住宅，但该住宅建筑面积超过当地廉租房保障面积的3倍（54㎡），或评估价值明显超过当地普通商品房均价，被执行人亦未主张其本人及所扶养家属无其他生活来源，依据上述规定，该住房应当认定为可供执行财产。申请执行人同意从变价款中优先扣除5至8年租金作为被执行人安置费用。"

---

## 战术二：终本转破产+出资加速到期跃迁（EXEC_END_P程 → 破）

### 实务痛点

执行局查控一圈无果后，往往开具《终结本次执行程序裁定书》（终本）。终本后案件"石沉大海"，律师难以推动。但破产程序或追加认缴未届期股东，可以从根本盘活"空壳公司终本死案"。

### 法律依据

| 层级 | 依据 | 内容 |
|------|------|------|
| 《公司法》2024新 | 第54条 | 股东出资加速到期（公司不能清偿到期债务） |
| 《公司法》2024新 | 第88条 | 瑕疵股权转让，股权受让人与转让人连带责任 |
| 司法解释 | 《执行转破产意见》 | 执行案件移送破产审查的操作规程 |
| 司法解释 | 《追加变更被执行人规定》第17条 | 未缴纳出资的股东可被追加为被执行人 |

### 双重路径触发

```
【案件状态 = 终本】+【被执行人 = 企业法人】
    ↓
┌─────────────────────────┬──────────────────────────┐
│  路径A：执转破（核武级） │  路径B：追加股东（直接追加） │
├─────────────────────────┼──────────────────────────┤
│ 触发条件：               │  触发条件：               │
│ ① 被执行人为企业法人    │  ① 股东认缴出资未届期     │
│ ② 确认无财产可供执行   │  ② 公司不能清偿债务       │
│ ③ 申请执行人同意移送   │  ③ 出资期限约定不明/过长  │
│                          │                           │
│ 输出：                   │  输出：                   │
│ 《执行转破产审查申请书》 │ 《追加认缴未届期股东申请书》 │
│                          │                           │
│ 效果：                   │  效果：                   │
│ 破产受理后，所有债权    │  股东出资义务依法加速到期  │
│ 平等受偿，但可通过破产  │  → 冻结/扣划股东个人账户  │
│ 撤销权追回逃废债资产   │                           │
└─────────────────────────┴──────────────────────────┘
```

### 路径A详解：执转破（执行转破产）

```python
def trigger_execution_to_bankruptcy(case_json):
    """
    当终本案件 + 企业法人被执行人时，触发执转破链路
    法律依据：《企业破产法》第2条 + 《执行转破产意见》
    """
    respondent = case_json["parties"]["respondent"]
    company_name = case_json["case_info"].get("respondent_company", respondent)

    # 核验是否为企查查已登记的企业法人
    if not is_company(company_name):
        return {"eligible": False, "reason": "非企业法人，不适用执转破"}

    # 核验是否有认缴出资未届期股东
    unpaid_capital = query_qcc_unpaid_capital(company_name)
    if unpaid_capital > 0:
        return {
            "eligible": True,
            "primary_route": "追加股东（路径B）",
            "secondary_route": "执转破（路径A）",
            "unpaid_capital": unpaid_capital,
            "recommended_sequence": "先追加股东（快），后执转破（彻底）"
        }

    # 无资产企查查 → 执转破
    return {
        "eligible": True,
        "route": "执转破（路径A）",
        "documents_needed": [
            "执行转破产审查申请书",
            "执行案件终本裁定书复印件",
            "被执行企业财产查询情况说明",
            "申请执行人身份证明及授权委托书"
        ],
        "court": "被执行人住所地中级人民法院"
    }
```

### 路径B详解：新公司法第54条出资加速到期

```python
def trigger_capital_acceleration(case_json):
    """
    新《公司法》第54条：股东出资加速到期
    触发条件：公司不能清偿到期债务
    关键证据：终本裁定书（证明"不能清偿"）
    """
    return {
        "statute": "《中华人民共和国公司法》（2024）第54条",
        "content": "公司不能清偿到期债务的，债权人有权要求已认缴出资但未届出资期限的股东提前缴纳出资。",
        "application": "被执行企业被终本 → 证明其不能清偿到期债务 → 认缴股东出资义务加速到期",
        "litigation_route": "路径B1：直接追加（快，适用执行程序）\n路径B2：另行起诉（全面，适用股东损害债权人利益纠纷）",
        "key_evidence": [
            "终本裁定书（证明公司无财产）",
            "公司章程（证明认缴期限）",
            "工商登记信息（证明股东身份及认缴金额）"
        ]
    }
```

### 输出交付物

**文书编号：文书88（追加认缴未届期股东）**
- 《追加认缴未届期股东为被执行人申请书》（路径B）
- 《执行转破产审查申请书》（路径A）

---

## 战术三：穿透隐匿财产特征库扩展（EXEC_ASSET_HIDING）

### 实务痛点

现代老赖的财产隐匿手段已从"个人银行卡"升级到：
- 具有现金价值的商业保险（年金险、分红险、终身寿险）
- 微信/支付宝商户收款号
- 转移至第三人名下的到期债权

### 三大新型隐匿财产穿透

#### 3.1 商业保险现金价值执行

```python
INSURANCE_POLICY_INDICATORS = {
    "线索关键词": ["保险", "年金", "分红", "寿险", "万能险", "投连险", "保单贷款"],
    "申请调查令": "向银保监局申请调取被执行人投保信息（商业保险）",
    "法律依据": [
        "《最高人民法院关于人民法院执行工作若干问题的规定（试行）》第16条",
        "《保险法》第47条（保险单现金价值）",
        "《民事诉讼法》第249条（到期债权执行）"
    ],
    "执行步骤": [
        "① 向法院申请开具调查令（律师调查令）→ 调取保单信息",
        "② 发现保单 → 申请法院向保险公司发出《协助执行通知书》",
        "③ 保险公司回函确认现金价值",
        "④ 法院作出划拨裁定 → 保险公司将现金价值划至法院执行账户",
        "⑤ 注意：保险合同未到期前，被保险人不同意退保 → 可先冻结，待期满后强制退保"
    ],
    "特殊注意": "人身意外险、医疗险等不具现金价值，不在执行范围"
}

def handle_insurance_policy_investigation(case_json):
    """商业保险现金价值执行模块"""
    return INSURANCE_POLICY_INDICATORS
```

#### 3.2 微信/支付宝商户收款号执行

```python
MERCHANT_ACCOUNT_INDICATORS = {
    "线索关键词": ["商户", "收款", "二维码", "经营", "店铺", "贸易公司", "个体工商户"],
    "申请调查令": "向财付通（微信支付）/蚂蚁集团（支付宝）申请交易流水",
    "法律依据": [
        "《民事诉讼法》第249条（网络资金执行）",
        "《非银行支付机构客户备付金存管办法》",
        "《最高人民法院关于网络查询被执行人存款的复函》"
    ],
    "执行步骤": [
        "① 向法院申请调查令 → 调取财付通/支付宝绑定商户信息",
        "② 发现商户号 → 申请法院向财付通/支付宝发出《协助冻结通知书》",
        "③ 调取近3年交易流水 → 锁定隐匿资金去向",
        "④ 如资金流向案外人 → 触发债权人撤销权（民法典§538）"
    ],
    "高危信号": "商户号注册人不是被执行人本人（借用他人身份）→ 追加实际控制人为被执行人"
}
```

#### 3.3 第三人到期债权执行

```python
DEBT_RECEIVABLE_INDICATORS = {
    "线索关键词": ["欠款", "应收账款", "货款", "租金", "债权", "转让"],
    "申请调查令": "要求被执行人如实申报 + 向已知债务人发出协助执行通知",
    "法律依据": [
        "《民事诉讼法》第249条（到期债权执行）",
        "《执行规定》第45条（第三人履行债务）"
    ],
    "执行步骤": [
        "① 被执行人接到《报告财产令》后拒不报告或虚假报告 → 拘留/罚款",
        "② 发现第三人对被执行人有到期债务 → 申请法院向第三人发出《履行到期债务通知书》",
        "③ 第三人在15日内提出异议 → 不得强制执行（告知另行起诉）",
        "④ 第三人无异议 → 法院强制执行该第三人"
    ],
    "关键证据": "合同 + 发票 + 送货单 + 催款记录 → 证明到期债权存在"
}
```

### 财产线索矩阵（新增）

```json
{
  "asset_type_expansion": {
    "商业保险现金价值": {
      "detection_keywords": ["保险", "年金", "分红险", "万能险", "寿险"],
      "investigation_method": "律师调查令 → 银保监局/保险公司",
      "enforcement_method": "强制退保 + 划拨现金价值",
      "template_id": "文书88"
    },
    "微信/支付宝商户号": {
      "detection_keywords": ["商户收款", "二维码经营", "个体工商户"],
      "investigation_method": "律师调查令 → 财付通/蚂蚁集团",
      "enforcement_method": "冻结商户账户 + 扣划余额",
      "template_id": "文书89"
    },
    "第三人到期债权": {
      "detection_keywords": ["欠款", "应收账款", "应付账款"],
      "investigation_method": "被执行人报告 + 第三人调查",
      "enforcement_method": "履行债务通知 → 强制执行",
      "template_id": "文书90"
    }
  }
}
```

---

## 战术四：程序时效守护神（EXEC_STATUTE_LIMIT_GUARD）

### 实务痛点

执行程序中的法定时效极其严苛，一旦错过永久丧失救济权：

| 时效类型 | 期限 | 法律后果 |
|---------|------|---------|
| 申请执行复议 | 10日（裁定送达） | 丧失复议权 |
| 提出执行异议 | 15日（裁定送达） | 丧失异议权 |
| **执行异议之诉** | **15日（裁定送达）** | **永久丧失实体救济权** |
| 申请不予执行仲裁 | 15日（裁定送达） | 永久丧失不予执行权 |
| 申请再审 | 6个月（裁定送达） | 永久丧失再审权 |

### 15天黄金期：执行异议之诉时效

这是最致命、最容易导致律师"执业责任事故"的时效：

```
【法院作出《执行异议裁定书》/《驳回申请裁定书》】
    ↓
【律师输入"裁定书签收日期"（强制要求）】
    ↓
【系统自动启动"15天黄金起诉倒计时"】
    ↓
【飞书卡片高亮警报 + 律所门户倒计时显示】
    ↓
【一键备妥《执行异议之诉起诉状》】
    ↓
【律师确认无误 → 提交法院】
```

### Timeline Guard 核心逻辑

```python
from datetime import datetime, timedelta

CRITICAL_DEADLINES = {
    "执行异议之诉": {
        "statute": "《民事诉讼法》第234条",
        "days": 15,
        "unit": "自然日（含节假日）",
        "warning_levels": [
            {"day": 15, "label": "最后一天！", "color": "RED", "urgency": "IMMEDIATE"},
            {"day": 10, "label": "仅剩5天", "color": "ORANGE", "urgency": "HIGH"},
            {"day": 7, "label": "仅剩7天", "color": "YELLOW", "urgency": "MEDIUM"},
            {"day": 3, "label": "仅剩3天", "color": "YELLOW", "urgency": "MEDIUM"},
        ],
        "consequence": "永久丧失实体救济权（错过即为执业责任事故）"
    },
    "申请执行复议": {
        "statute": "《民事诉讼法》第250条",
        "days": 10,
        "unit": "工作日",
        "warning_levels": [
            {"day": 10, "label": "最后一天！", "color": "RED", "urgency": "IMMEDIATE"},
            {"day": 5, "label": "仅剩5天", "color": "ORANGE", "urgency": "HIGH"},
        ],
        "consequence": "丧失复议权"
    }
}

def calculate_deadline(receipt_date_str, case_type="执行异议之诉"):
    """
    计算时效截止日
    receipt_date_str: 裁定书签收日期（YYYY-MM-DD）
    """
    config = CRITICAL_DEADLINES[case_type]
    receipt_date = datetime.strptime(receipt_date_str, "%Y-%m-%d")
    deadline = receipt_date + timedelta(days=config["days"])

    remaining = (deadline - datetime.now()).days

    return {
        "case_type": case_type,
        "receipt_date": receipt_date_str,
        "deadline_date": deadline.strftime("%Y-%m-%d"),
        "remaining_days": remaining,
        "warning_level": next(
            (w for w in config["warning_levels"] if remaining <= w["day"]),
            None
        ),
        "expired": remaining < 0,
        "statute": config["statute"],
        "consequence": config["consequence"]
    }
```

### 倒计时触发机制

```python
def activate_timeline_guard(case_json, receipt_date, case_type):
    """
    激活时效守护
    在 case.json 中新增 timeline_guard 节点
    """
    deadline_info = calculate_deadline(receipt_date, case_type)

    if deadline_info["expired"]:
        return {
            "status": "EXPIRED",
            "message": f"【严重】{case_type}时效已于 {deadline_info['deadline_date']} 届满，永久丧失救济权！",
            "urgent_action": "立即向律所主任报告，启动内部问责"
        }

    # 更新 case.json
    case_json["timeline_guard"] = {
        "active": True,
        "case_type": case_type,
        "receipt_date": receipt_date,
        "deadline_date": deadline_info["deadline_date"],
        "remaining_days": deadline_info["remaining_days"],
        "warning_level": deadline_info["warning_level"],
        "activated_at": datetime.now().isoformat()
    }

    # 同步启动飞书倒计时卡片
    if deadline_info["remaining_days"] <= 10:
        send_feishu_countdown_card(case_json, deadline_info)

    return {
        "status": "ACTIVE",
        "deadline_info": deadline_info,
        "next_action": "立即准备起诉状"
    }
```

### 输出交付物

**文书编号：文书92（执行异议之诉起诉状）**
- 《执行异议之诉起诉状》+ 证据清单 + 诉讼保全申请书

---

## 四战术综合调度矩阵

| 战术 | 代码 | 优先级 | 触发条件 | 输出文书 |
|------|------|--------|---------|---------|
| 唯一住房执行 | EXEC_SOLE_HOUSING | P0 | 住宅 + 唯一住房抗辩 | 文书91 |
| 终本转破产+出资加速到期 | EXEC_END_TO_BANKRUPTCY | P0 | 终本 + 企业法人 | 文书88 |
| 商业保险现金价值 | EXEC_INSURANCE_VALUE | P0 | 发现保单线索 | 文书88附 |
| 微信/支付宝商户号 | EXEC_MERCHANT_ACCOUNT | P0 | 发现商户线索 | 文书89 |
| 第三人到期债权 | EXEC_DEBT_RECEIVABLE | P0 | 发现到期债权 | 文书90 |
| 程序时效守护 | EXEC_STATUTE_LIMIT_GUARD | P1 | 收到裁定书 | 文书92 |

---

*最后更新：2026-06-13 | V7.0 执行特种战术扩展*