#!/usr/bin/env python3
"""
weixiaolv-execution-penalty/scripts/trigger_checker.py
拒执罪"情节严重"特征码检测器

依据：
- 法释〔2024〕13号《最高人民法院、最高人民检察院关于办理拒不执行判决、裁定刑事案件适用法律若干问题的解释》
- 法发〔2025〕8号《关于办理拒不执行判决、裁定刑事案件若干问题的意见》（两高一部，2025-07-01施行）

功能：
输入 case.json 的执行状态快照，输出"情节严重"特征码匹配矩阵 + 犯罪嫌疑评分。
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class SeverityLevel(Enum):
    """拒执罪严重程度等级"""
    NOT_QUALIFIED = "不构成犯罪"
    QUALIFIED = "构成犯罪（一般情节）"
    ESPECIALLY_SERIOUS = "情节特别严重（3-7年）"


@dataclass
class TriggerMatch:
    """单个特征码匹配结果"""
    code: str                              # 特征码编号
    description: str                        # 特征描述
    legal_basis: str                        # 对应法条
    matched: bool                           # 是否命中
    evidence_status: str                    # 证据状态：complete/partial/missing
    severity_level: str                     # 严重程度：general/especially_serious


class TriggerChecker:
    """
    2024两高解释 + 2025两高一部意见 核心情节严重特征码检测引擎
    """

    # 十大"情节严重"情形（法释〔2024〕13号 第三条）
    # + "情节特别严重"情形（法释〔2024〕13号 第四条）
    TRIGGER_PATTERNS = [
        # ── 一般情节（第三条）───────────────────────────────
        {
            "code": "T1",
            "description": "被执行人隐藏、转移、故意损毁财产或者无偿转让财产、以明显不合理的价格转让财产，致使判决、裁定无法执行",
            "legal_basis": "刑法§313 + 2024解释§3(一)",
            "severity": "general",
            "keywords": ["隐藏财产", "转移财产", "无偿转让", "低价转让", "损毁财产"],
        },
        {
            "code": "T1.5",  # ← 黄金窗口！2024解释新规
            "description": "被执行人隐藏、转移、故意损毁财产或者无偿转让财产、以明显不合理的价格转让财产，**在判决、裁定生效前**即已开始，致使判决、裁定无法执行",
            "legal_basis": "2024解释§3(一)（新增：犯罪时间前移至判决生效前）",
            "severity": "general",
            "keywords": ["判决生效前转移", "诉前转移财产", "起诉前转让", "保全前转移"],
            "note": "⚠️ T1.5 是2024解释最大亮点：故意犯罪预备行为可追溯！"
        },
        {
            "code": "T2",
            "description": "被执行人与他人串通，通过虚假诉讼、仲裁、调解等方式妨害执行，致使判决、裁定无法执行",
            "legal_basis": "刑法§313 + 2024解释§3(二)",
            "severity": "general",
            "keywords": ["虚假诉讼", "虚假仲裁", "虚假调解", "恶意串通", "倒签合同"],
        },
        {
            "code": "T3",
            "description": "拒不交出或者妨害搜醒被执行人可供执行的财产或者票据、证照，致使判决、裁定无法执行",
            "legal_basis": "刑法§313 + 2024解释§3(三)",
            "severity": "general",
            "keywords": ["拒不交出财产", "隐藏票据", "隐藏证照", "抗拒搜醒"],
        },
        {
            "code": "T4",
            "description": "被执行人、担保人有履行能力但拒不执行，**经采取司法拘留措施后仍不执行**",
            "legal_basis": "刑法§313 + 2024解释§3(四)",
            "severity": "general",
            "keywords": ["拘留后仍不执行", "司法拘留", "拘留不履行"],
            "note": "⚠️ 司法拘留是激活拒执罪的法定前置条件之一！"
        },
        {
            "code": "T5",
            "description": "被执行人违反限制消费令、限制高消费令，**经采取罚款措施后仍不执行**，且具有高消费行为",
            "legal_basis": "刑法§313 + 2024解释§3(五)",
            "severity": "general",
            "keywords": ["违反限高", "限高后高消费", "乘坐飞机", "高铁G字头", "入住星级酒店"],
        },
        {
            "code": "T6",
            "description": "被执行人虚假报告财产或者伪造、变造有关财产证据的材料，或者指使、贿胁他人作伪证，妨害执行",
            "legal_basis": "刑法§313 + 2024解释§3(六)",
            "severity": "general",
            "keywords": ["虚假报告财产", "伪造证据", "指使作伪证", "伪造财产证明"],
        },
        {
            "code": "T7",
            "description": "负有执行义务的人有 Capacity（能力）拒不执行，**转移、隐藏、变卖、赠与、挥霍财产或者与家庭成员共有财产**",
            "legal_basis": "刑法§313 + 2024解释§3(七)",
            "severity": "general",
            "keywords": ["转移共有财产", "赠与财产", "挥霍财产", "隐藏家庭共有财产"],
        },
        {
            "code": "T8",
            "description": "其他有能力执行拒不执行，情节严重的行为",
            "legal_basis": "刑法§313 + 2024解释§3(八)",
            "severity": "general",
            "keywords": ["其他情节严重"],
        },
        # ── 情节特别严重（第四条）────────────────────────
        {
            "code": "TS1",
            "description": "被执行人实施 T1/T1.5/T7 类行为，**致使判决、裁定无法执行**的款项数额特别巨大（个人≥100万，单位≥500万）",
            "legal_basis": "2024解释§4(一)",
            "severity": "especially_serious",
            "keywords": ["转移数额巨大", "100万以上", "单位500万以上"],
        },
        {
            "code": "TS2",
            "description": "哄闹、冲击执行现场，**聚众拒不排除执行干扰**，致使执行工作无法进行",
            "legal_basis": "2024解释§4(二)",
            "severity": "especially_serious",
            "keywords": ["哄闹执行现场", "聚众冲击", "暴力抗拒执行"],
        },
        {
            "code": "TS3",
            "description": "**被执行人以外的其他人**拒不交付财物或者协助执行义务，导致执行标的物灭失、无法恢复原状",
            "legal_basis": "2024解释§4(三)",
            "severity": "especially_serious",
            "keywords": ["第三人拒不协助", "导致财产灭失", "无法恢复"],
        },
    ]

    # 中文↔英文证据字段别名映射（支持 case.json 中文键名和脚本英文键名）
    FIELD_ALIASES = {
        "judgment_copy": ["judgment_copy", "判决书副本", "判决书", "生效判决"],
        "enforcement_notice": ["enforcement_notice", "执行通知书", "执行案件受理通知书"],
        "ability_to_pay": ["ability_to_pay", "有履行能力", "有能力执行", "有履行能力证据"],
        "transfer_agreement": ["transfer_agreement", "车辆过户协议", "过户协议", "转让协议"],
        "transfer_records": ["transfer_records", "车管所过户档案", "过户档案", "车辆过户记录"],
        "timeline_proof": ["timeline_proof", "判决生效日", "过户日", "时间线",
                          "timeline_proof_judgment_vs_transfer"],
        "high_consumption_record": ["high_consumption_record", "机票订单", "高消费记录", "消费记录"],
        "limit_high_consumer_order": ["limit_high_consumer_order", "限高令"],
        "limit_high_consumer_delivery_record": ["limit_high_consumer_delivery_record",
                                                "限高令送达回证", "送达回证"],
        "detention_record": ["detention_record", "拘留决定书", "拘留执行回执"],
    }

    def __init__(self):
        self.results: List[TriggerMatch] = []

    def check(self, case_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        主检测入口

        Args:
            case_state: case.json 的执行状态快照
                facts: 执行行为事实（含 keywords + 证据字段）
                violations_detected: 违规行为列表（description 含关键词即可触发）
                assets_discovered: 资产列表

        Returns:
            {
                "overall_score": float,          # 0.0-1.0，犯罪嫌疑评分
                "severity_level": SeverityLevel,  # 严重程度
                "matched_triggers": [TriggerMatch],
                "primary_trigger": str,           # 主特征码
                "primary_evidence_gaps": [str],   # 主要证据缺口
                "prosecution_ready": bool,         # 是否具备追刑条件
                "narrative": str                   # 生成给律师的核验报告文本
            }
        """
        self.results = []
        facts = case_state.get("facts", {})
        violations = case_state.get("violations_detected", [])
        assets = case_state.get("assets_discovered", [])

        matched = []
        primary_evidence_gaps = []

        for pattern in self.TRIGGER_PATTERNS:
            match_result = self._match_pattern(pattern, facts, violations, assets)
            self.results.append(match_result)
            if match_result.matched:
                matched.append(match_result)

        if not matched:
            return self._empty_result()

        score = self._compute_score(matched)
        severity = self._determine_severity(matched)
        primary = max(matched, key=lambda m: self._evidence_weight(m.evidence_status))

        for r in matched:
            if r.evidence_status != "complete":
                primary_evidence_gaps.append(f"[{r.code}] {r.description}：证据{r.evidence_status}")

        prosecution_ready = (
            score >= 0.70
            and primary.evidence_status in ("complete", "partial")
        )

        narrative = self._build_narrative(matched, score, severity, primary, primary_evidence_gaps)

        return {
            "overall_score": round(score, 3),
            "severity_level": severity.value,
            "matched_triggers": [
                {"code": r.code, "description": r.description,
                 "legal_basis": r.legal_basis, "evidence_status": r.evidence_status}
                for r in matched
            ],
            "primary_trigger": primary.code,
            "primary_evidence_gaps": primary_evidence_gaps,
            "prosecution_ready": prosecution_ready,
            "narrative": narrative,
        }

    def _match_pattern(
        self,
        pattern: Dict[str, Any],
        facts: Dict[str, Any],
        violations: List[Dict[str, Any]],
        assets: List[Dict[str, Any]],
    ) -> TriggerMatch:
        """检测单个特征码是否命中"""
        code = pattern["code"]
        keywords = pattern["keywords"]

        # 关键词匹配：搜索 facts 描述文本 + violations 列表
        all_text = " ".join([
            facts.get("description", ""),
            facts.get("transfer_description", ""),
            " ".join([v.get("description", "") for v in violations]),
        ]).lower()

        matched_keywords = [kw for kw in keywords if kw.lower() in all_text]

        # 证据状态评估（支持中英文字段别名）
        evidence_status = self._assess_evidence(code, facts, violations, assets)

        return TriggerMatch(
            code=code,
            description=pattern["description"],
            legal_basis=pattern["legal_basis"],
            matched=len(matched_keywords) > 0,
            evidence_status=evidence_status,
            severity_level=pattern["severity"],
        )

    def _has_field(self, field_keys: list, facts: Dict[str, Any]) -> bool:
        """检查任意字段别名是否存在且值为真（非None/非空字符串）"""
        for key in field_keys:
            val = facts.get(key)
            if val is not None and val != "" and val is not False:
                return True
        return False

    def _count_satisfied(self, required_keys: list, facts: Dict[str, Any]) -> int:
        """统计有多少个所需字段存在且值非空"""
        aliases = [self.FIELD_ALIASES.get(k, [k]) for k in required_keys]
        return sum(1 for alias_list in aliases if self._has_field(alias_list, facts))

    def _assess_evidence(
        self,
        code: str,
        facts: Dict[str, Any],
        violations: List[Dict[str, Any]],
        assets: List[Dict[str, Any]],
    ) -> str:
        """评估某特征码的证据完成度（支持中英文字段别名）"""
        # 基础证据包（三项全有 = base_complete）
        base_keys = ["judgment_copy", "enforcement_notice", "ability_to_pay"]
        base_satisfied = self._count_satisfied(base_keys, facts)
        base_complete = base_satisfied == len(base_keys)

        if not base_complete:
            return "missing"

        # 各特征码专项证据
        specific_evidence_map = {
            "T1":   ["transfer_agreement", "transfer_records"],
            "T1.5": ["transfer_agreement", "transfer_records", "timeline_proof"],
            "T2":   ["transfer_agreement"],
            "T4":   ["detention_record"],
            "T5":   ["high_consumption_record",
                     "limit_high_consumer_order",
                     "limit_high_consumer_delivery_record"],
            "T6":   ["transfer_agreement"],
            "T7":   ["transfer_agreement", "transfer_records"],
            "TS1":  ["transfer_agreement", "timeline_proof"],
        }

        required = specific_evidence_map.get(code, [])
        if not required:
            return "complete" if base_complete else "partial"

        satisfied = self._count_satisfied(required, facts)
        if satisfied == len(required):
            return "complete"
        elif satisfied > 0:
            return "partial"
        else:
            return "missing"

    def _compute_score(self, matched: List[TriggerMatch]) -> float:
        """
        计算综合犯罪嫌疑评分

        公式：total_weight / matched_count
        - complete 权重 1.0，partial 权重 0.6，missing 权重 0.2
        - 3个 partial 特征码 → (0.6+0.6+0.6)/3 = 0.6 = 60%
        - 3个 complete 特征码 → (1.0+1.0+1.0)/3 = 1.0 = 100%
        """
        if not matched:
            return 0.0

        weights = {"complete": 1.0, "partial": 0.6, "missing": 0.2}
        severity_boost = {"general": 1.0, "especially_serious": 1.3}

        total = 0.0
        for m in matched:
            w = weights.get(m.evidence_status, 0.5)
            s = severity_boost.get(m.severity_level, 1.0)
            total += w * s

        # 归一化：以命中的特征码数量为分母
        raw_score = total / len(matched)
        return min(1.0, raw_score)

    def _determine_severity(self, matched: List[TriggerMatch]) -> SeverityLevel:
        if any(m.severity_level == "especially_serious" for m in matched):
            return SeverityLevel.ESPECIALLY_SERIOUS
        elif any(m.matched for m in matched):
            return SeverityLevel.QUALIFIED
        else:
            return SeverityLevel.NOT_QUALIFIED

    def _evidence_weight(self, status: str) -> float:
        return {"complete": 1.0, "partial": 0.6, "missing": 0.2}.get(status, 0.0)

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "overall_score": 0.0,
            "severity_level": SeverityLevel.NOT_QUALIFIED.value,
            "matched_triggers": [],
            "primary_trigger": None,
            "primary_evidence_gaps": ["缺基本犯罪构成证据"],
            "prosecution_ready": False,
            "narrative": "未发现符合拒执罪构成要件的逃债行为特征，建议继续搜集财产线索。",
        }

    def _build_narrative(
        self,
        matched: List[TriggerMatch],
        score: float,
        severity: SeverityLevel,
        primary: TriggerMatch,
        gaps: List[str],
    ) -> str:
        lines = [
            "═" * 60,
            "  拒执罪五要件评估报告",
            "═" * 60,
            f"  犯罪嫌疑评分：{score:.0%}",
            f"  严重程度：{severity.value}",
            f"  主特征码：{primary.code} — {primary.description[:40]}...",
            f"  法律依据：{primary.legal_basis}",
            "",
            "  命中特征码清单：",
        ]
        for m in matched:
            emoji = "✅" if m.evidence_status == "complete" else "⚠️" if m.evidence_status == "partial" else "❌"
            lines.append(f"  {emoji} [{m.code}] {m.description[:45]}...")
            lines.append(f"      法律依据：{m.legal_basis} | 证据：{m.evidence_status}")

        if gaps:
            lines += ["", "  ⚠️ 证据缺口（需补齐后再追刑）："]
            for g in gaps:
                lines.append(f"  • {g}")

        lines += ["", f"  追刑就绪：{'✅ 是' if score >= 0.70 else '❌ 否（评分不足70%）'}"]
        lines.append("═" * 60)
        return "\n".join(lines)


# ── CLI 调试入口 ──────────────────────────────────────────
if __name__ == "__main__":
    import json

    checker = TriggerChecker()

    sample_state = {
        "facts": {
            "description": "王五在判决生效后将其名下奔驰车以0元过户给小舅子李六，同时被限制高消费后仍乘坐飞机头等舱出差",
            "transfer_description": "0元过户车辆给关联人",
            "judgment_copy": "有",          # 有生效判决
            "enforcement_notice": "有",     # 有执行通知书
            "ability_to_pay": "有",          # 有履行能力
            "high_consumption_record": "有", # 限消后高消费
            "transfer_agreement": "有",     # 过户协议
            "detention_record": None,
        },
        "violations_detected": [
            {"type": "VIOLATE_HEIGHT_LIMIT", "description": "限消后乘坐飞机头等舱"},
            {"type": "ASSET_TRANSFER", "description": "0元过户车辆给关联人"},
        ],
        "assets_discovered": [
            {"type": "REAL_ESTATE", "is_sole_residence": False},
            {"type": "BANK_ACCOUNT", "balance": 50000},
        ]
    }

    result = checker.check(sample_state)
    print(result["narrative"])
    print("\n[JSON]", json.dumps({k: v for k, v in result.items() if k != "narrative"}, ensure_ascii=False, indent=2))