#!/usr/bin/env python3
"""
weixiaolv-execution-penalty/scripts/evidence_mapper.py
拒执罪刑事证据链映射器（排除合理怀疑标准）

依据：
- 刑事诉讼法§55（排除合理怀疑）
- 2024解释§1-14（各情节严重的证据要求）
- 2025意见§1-18（证据标准）

功能：
输入 case.json 的已知证据状态，输出：
1. 完整证据链映射表（要素→证据→状态）
2. 证据缺口 GAP 清单
3. 自动生成的《律师调查令申请书》（针对缺口证据）
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class EvidenceStandard(Enum):
    """刑事证明标准"""
    CIVIL_PREPONDERANCE = "民事优势证据（举证责任）"
    CRIMINAL_BEYOND_REASONABLE_DOUBT = "排除合理怀疑（刑事）"


@dataclass
class EvidenceElement:
    """单个证据要素"""
    element_id: str
    description: str                          # 证据要素描述
    legal_nature: str                         # 属于哪类证据（书证/物证/电子数据等）
    standard: EvidenceStandard                # 证明标准
    burden_party: str                         # 举证责任方：自诉人/被告人
    status: str                               # 状态：complete/partial/missing
    existing_evidence: List[str] = field(default_factory=list)   # 已有证据
    missing_evidence: List[str] = field(default_factory=list)   # 缺失证据
    suggestion: str = ""                       # 补强建议


class EvidenceMapper:
    """
    拒执罪刑事证据链映射器

    核心方法：输入已知证据 → 输出证据链健康度报告 + 调查令申请书
    """

    # 拒执罪四大构成要件 × 各情节的证据要素清单
    CRIME_ELEMENTS = {
        # ── 要件一：负有执行义务 ──────────────────────────
        "OBLIGATION": {
            "description": "被执行人对申请执行人负有执行义务（生效法律文书确认）",
            "elements": [
                {
                    "element_id": "OBL_01",
                    "description": "生效法律文书（判决/裁定/调解书/公证债权文书）",
                    "legal_nature": "书证",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人（公诉机关）",
                    "keywords": ["判决书", "裁定书", "调解书", "公证债权文书"],
                },
                {
                    "element_id": "OBL_02",
                    "description": "执行案件受理证明（执行立案文书）",
                    "legal_nature": "书证",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人",
                    "keywords": ["执行案件受理通知书", "执行立案"],
                },
                {
                    "element_id": "OBL_03",
                    "description": "执行通知书送达回证（证明已依法送达）",
                    "legal_nature": "书证（送达回证）",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人",
                    "keywords": ["执行通知书", "送达回证"],
                },
            ]
        },
        # ── 要件二：有能力执行 ────────────────────────────
        "CAPACITY": {
            "description": "被执行人有能力执行生效法律文书确定的义务",
            "elements": [
                {
                    "element_id": "CAP_01",
                    "description": "被执行人当前有可供执行的财产（银行账户/房产/车辆/股权/保单）",
                    "legal_nature": "财产凭证/调查报告",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人（通过调查令获取）",
                    "keywords": ["银行流水", "不动产登记", "车辆登记", "保单", "股权"],
                },
                {
                    "element_id": "CAP_02",
                    "description": "被执行人在判决生效后/执行期间有高消费行为（证明有履行能力）",
                    "legal_nature": "消费记录/电子数据",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人",
                    "keywords": ["机票订单", "酒店预订", "高铁G字头", "高尔夫", "奢侈品"],
                },
                {
                    "element_id": "CAP_03",
                    "description": "被执行人名下财产变动记录（证明有财产变动能力）",
                    "legal_nature": "财产变动记录",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人",
                    "keywords": ["银行流水", "房产交易记录", "车辆过户记录"],
                },
            ]
        },
        # ── 要件三：拒不执行（核心）────────────────────
        "REFUSAL": {
            "description": "被执行人采取积极作为或不作为方式拒不执行",
            "elements": [
                {
                    "element_id": "REF_01",
                    "description": "被执行人实施了转移、隐匿、变卖、赠与财产的行为",
                    "legal_nature": "行为证据（书证+电子数据）",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人",
                    "keywords": ["过户协议", "转账凭证", "赠与合同", "财产转让协议"],
                },
                {
                    "element_id": "REF_02",
                    "description": "被执行人违反限制消费令进行高消费",
                    "legal_nature": "消费记录（电子数据）",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人",
                    "keywords": ["限高令送达回证", "机票", "星级酒店", "高尔夫"],
                },
                {
                    "element_id": "REF_03",
                    "description": "被执行人虚假报告财产或伪造财产证据材料",
                    "legal_nature": "书证（虚假材料）",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人",
                    "keywords": ["财产申报表", "虚假银行流水", "伪造产权证"],
                },
                {
                    "element_id": "REF_04",
                    "description": "被执行人经司法拘留后仍不执行（证明拒执故意）",
                    "legal_nature": "司法文书",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人",
                    "keywords": ["拘留决定书", "拘留执行回执"],
                },
            ]
        },
        # ── 要件四：情节严重 ────────────────────────────
        "SEVERITY": {
            "description": "被执行人的拒执行为达到'情节严重'标准",
            "elements": [
                {
                    "element_id": "SEV_01",
                    "description": "转移/隐匿财产的数额或价值（证明达到情节严重门槛）",
                    "legal_nature": "价值鉴定/评估报告",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人",
                    "keywords": ["资产评估报告", "财产价值鉴定", "数额证明"],
                },
                {
                    "element_id": "SEV_02",
                    "description": "转移行为的时间节点（在判决生效前/后）",
                    "legal_nature": "时间证据",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人",
                    "keywords": ["合同签订日期", "过户日期", "判决生效日期"],
                },
                {
                    "element_id": "SEV_03",
                    "description": "被执行人与受让人的关系（证明主观恶意）",
                    "legal_nature": "身份关系证据",
                    "standard": EvidenceStandard.CRIMINAL_BEYOND_REASONABLE_DOUBT,
                    "burden_party": "自诉人（用于推定知情）",
                    "keywords": ["户籍信息", "婚姻档案", "工商登记", "亲属关系证明"],
                },
            ]
        }
    }

    def __init__(self):
        self.elements: List[EvidenceElement] = []

    def map(self, case_state: Dict[str, Any], matched_triggers: List[str] = None) -> Dict[str, Any]:
        """
        主映射入口

        Args:
            case_state: case.json 的已知证据状态
            matched_triggers: trigger_checker.py 输出的命中特征码列表

        Returns:
            {
                "overall_chain_health": float,           # 0.0-1.0 证据链完整度
                "burden_shift_result": str,              # 举证责任是否移转
                "elements": [EvidenceElement],
                "gaps": [str],                            # 证据缺口清单
                "investigation_applications": [str],     # 律师调查令申请书文本
                "chain_health_report": str               # 给律师的核验报告
            }
        """
        self.elements = []
        known_evidence = case_state.get("known_evidence", {})

        all_gaps = []
        investigation_drafts = []

        for requirement_name, requirement_data in self.CRIME_ELEMENTS.items():
            for elem_spec in requirement_data["elements"]:
                elem = self._assess_element(elem_spec, known_evidence)
                self.elements.append(elem)
                if elem.status != "complete":
                    all_gaps.append(f"[{elem.element_id}] {elem.description}：缺 {', '.join(elem.missing_evidence)}")
                    if elem.missing_evidence:
                        draft = self._draft_investigation_app(elem, case_state)
                        investigation_drafts.append(draft)

        # 计算综合证据链完整度
        total = len(self.elements)
        complete = sum(1 for e in self.elements if e.status == "complete")
        partial = sum(1 for e in self.elements if e.status == "partial")
        chain_health = (complete + partial * 0.5) / total if total > 0 else 0.0

        # 举证责任判断（刑事标准：自诉人承担，证明标准"排除合理怀疑"）
        burden_shift = (
            "自诉人已初步完成举证（证据链完整度≥70%），法院应认定待证事实成立。"
            if chain_health >= 0.70 else
            "自诉人举证尚未达到'排除合理怀疑'标准，建议先补齐以下证据缺口再提起自诉。"
        )

        report = self._build_report(chain_health, complete, partial, total, all_gaps)

        return {
            "overall_chain_health": round(chain_health, 3),
            "burden_shift_result": burden_shift,
            "elements": [
                {
                    "element_id": e.element_id,
                    "description": e.description,
                    "legal_nature": e.legal_nature,
                    "standard": e.standard.value,
                    "burden_party": e.burden_party,
                    "status": e.status,
                    "existing_evidence": e.existing_evidence,
                    "missing_evidence": e.missing_evidence,
                    "suggestion": e.suggestion,
                }
                for e in self.elements
            ],
            "gaps": all_gaps,
            "investigation_applications": investigation_drafts,
            "chain_health_report": report,
        }

    def _assess_element(
        self,
        elem_spec: Dict[str, Any],
        known_evidence: Dict[str, Any]
    ) -> EvidenceElement:
        """评估单个证据要素的完成状态"""
        element_id = elem_spec["element_id"]
        keywords = elem_spec["keywords"]

        # 在 known_evidence 中搜索匹配
        matched_keys = []
        for kw in keywords:
            for evidence_key, evidence_value in known_evidence.items():
                if kw.lower() in evidence_key.lower() or (isinstance(evidence_value, str) and kw in evidence_value):
                    matched_keys.append(evidence_key)

        existing = list(set(matched_keys))
        missing = [kw for kw in keywords if not any(kw in k for k in existing)]

        status = "complete" if len(existing) >= 2 else ("partial" if existing else "missing")

        suggestion = ""
        if missing:
            suggestion_map = {
                "判决书": "向执行法院档案室调取生效判决书副本",
                "执行通知书": "向执行法院调取执行通知书及送达回证",
                "送达回证": "向执行法院调取送达回证原件",
                "银行流水": "申请律师调查令（向银行调取）",
                "机票": "申请律师调查令（向航空公司/订票平台调取）",
                "酒店预订": "申请律师调查令（向酒店集团调取）",
                "高铁G字头": "申请律师调查令（向铁路总局调取）",
                "过户协议": "申请律师调查令（向车管所/不动产登记中心调取）",
                "户籍信息": "申请律师调查令（向公安机关调取）",
                "婚姻档案": "申请律师调查令（向民政局调取）",
                "拘留决定书": "向执行法院调取拘留决定书及执行回执",
                "资产评估报告": "委托有资质评估机构出具",
            }
            suggestion = "；".join([suggestion_map.get(m, f"申请律师调查令（向{m}调取）") for m in missing[:2]])

        return EvidenceElement(
            element_id=element_id,
            description=elem_spec["description"],
            legal_nature=elem_spec["legal_nature"],
            standard=elem_spec["standard"],
            burden_party=elem_spec["burden_party"],
            status=status,
            existing_evidence=existing,
            missing_evidence=missing,
            suggestion=suggestion,
        )

    def _draft_investigation_app(self, elem: EvidenceElement, case_state: Dict[str, Any]) -> str:
        """自动生成律师调查令申请书（针对某证据缺口）"""
        defendant = case_state.get("defendant", "被执行人")
        case_id = case_state.get("case_id", "未知案号")

        lines = [
            f"律师调查令申请书（{elem.description}）",
            f"  案号：{case_id}",
            f"",
            f"申请人（申请执行人）：{case_state.get('applicant', '申请执行人')}",
            f"",
            f"请求事项：",
            f"  申请人特委托律师前往【{', '.join(elem.missing_evidence)}】调查收集",
            f"  【{elem.description}】作为本案拒执罪证据使用。",
            f"",
            f"事实与理由：",
            f"  依据《民事诉讼法》第67条及《最高人民法院关于人民法院执行工作若干问题的规定》",
            f"  （试行）第28条，申请人需要上述证据材料证明被执行人{defendant}涉嫌拒执罪的",
            f"  犯罪事实，特申请律师调查令。",
            f"",
            f"  调查内容：{elem.description}",
            f"  证明对象：{elem.suggestion}",
            f"",
            f"此致",
            f"  【管辖法院】",
        ]
        return "\n".join(lines)

    def _build_report(
        self,
        chain_health: float,
        complete: int,
        partial: int,
        total: int,
        gaps: List[str]
    ) -> str:
        lines = [
            "═" * 60,
            "  拒执罪刑事证据链健康度报告",
            "═" * 60,
            f"  证据链完整度：{chain_health:.0%}（{complete}项完整 / {partial}项部分 / {total}项总计）",
            f"  证明标准：排除合理怀疑（刑事）",
            f"  举证责任：自诉人（公诉机关）",
            "",
            "  证据链四要件核验：",
        ]
        for req_name, req_data in self.CRIME_ELEMENTS.items():
            lines.append(f"  【{req_name}】{req_data['description']}")
            for elem in self.elements:
                if elem.element_id.startswith(req_name[:3].upper()):
                    emoji = "✅" if elem.status == "complete" else "⚠️" if elem.status == "partial" else "❌"
                    lines.append(f"    {emoji} {elem.element_id} {elem.description[:35]}")
                    if elem.missing_evidence:
                        lines.append(f"       → 缺：{', '.join(elem.missing_evidence)}")

        if gaps:
            lines += ["", "  ⚠️ 证据缺口清单："]
            for g in gaps[:5]:
                lines.append(f"  • {g}")
            if len(gaps) > 5:
                lines.append(f"  • ...还有{len(gaps)-5}项缺口")

        lines.append("═" * 60)
        return "\n".join(lines)


# ── CLI 调试入口 ──────────────────────────────────────────
if __name__ == "__main__":
    mapper = EvidenceMapper()

    sample_state = {
        "case_id": "CASE_WANG_WU_001",
        "defendant": "王五",
        "applicant": "李四",
        "known_evidence": {
            "判决书副本": "有",
            "执行通知书": "有",
            "送达回证": "有",
            "限高令送达回证": "有",
            "机票订单": "有",
            "车辆过户协议": "有",
            # 银行流水缺失
            # 户籍信息缺失（亲属关系）
        }
    }

    result = mapper.map(sample_state)
    print(result["chain_health_report"])
    print("\n[律师调查令草案]")
    for draft in result["investigation_applications"]:
        print(draft)
        print("─"*40)