#!/usr/bin/env python3
"""
weixiaolv-execution-penalty/scripts/route_selector.py
拒执罪刑事追责路径自适应决策树

依据：法发〔2025〕8号《关于办理拒不执行判决、裁定刑事案件若干问题的意见》
（最高人民法院、最高人民检察院、公安部，2025-07-01施行）

功能：
输入 case.json 的程序状态快照，输出合法的追刑路径：
  - PUBLIC_REFERRAL     提请执行法院移送公安机关立案侦查
  - PUBLIC_REPORT_FIRST 前往公安机关自主控告（起步路径）
  - PRIVATE_PROSECUTION 直接向执行法院提起刑事自诉（须满足前置条件）
  - NONE               实体构成要件不足，暂不可追责
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta


class ProsecutionRoute(Enum):
    """追刑路径枚举"""
    NONE = "NONE"                          # 暂不可追责
    COURT_PUBLIC_TRANSFER = "COURT_PUBLIC_TRANSFER"   # 法院移送公安（公诉）
    PUBLIC_REPORT_FIRST = "PUBLIC_REPORT_FIRST"       # 先行公安控告
    PRIVATE_PROSECUTION = "PRIVATE_PROSECUTION"       # 刑事自诉


@dataclass
class RouteDecision:
    """路径决策结果"""
    route: ProsecutionRoute
    action_required: str                   # 下一步动作
    target_template: str                    # 目标文书模板
    rationale: str                          # 决策理由（含法条索引）
    statutory_deadline: Optional[str]       # 法定时限提醒
    warnings: list                          # 注意事项


class RouteSelector:
    """
    2025年两高一部意见对齐：拒执罪追刑路径自适应决策树
    """

    # 2025意见第15-18条：刑事自诉前置条件
    PRIVATE_PROSECUTION_PREREQUISITES = [
        {
            "condition_id": "PSP_01",
            "description": "公安机关已作出不予立案决定，并出具《不予立案通知书》",
            "legal_basis": "2025意见第15条(一)",
            "evidence_required": ["不予立案通知书"],
        },
        {
            "condition_id": "PSP_02",
            "description": "人民检察院对被执行人（负有执行义务的人）作出不起诉决定",
            "legal_basis": "2025意见第15条(二)",
            "evidence_required": ["不起诉决定书"],
        },
        {
            "condition_id": "PSP_03",  # ← 最常用的突破口！
            "description": "公安机关接受控告材料后30日内未予书面答复（含既不立案也不出具不予立案通知）",
            "legal_basis": "2025意见第15条(三)",
            "evidence_required": ["控告材料投递凭证（快递单/回执）", "受案回执"],
            "note": "⏰ 30天窗口期：从递交控告材料之日起算，律师须保留投递凭证！"
        },
    ]

    def determine_route(self, case_state: Dict[str, Any]) -> RouteDecision:
        """
        主决策入口

        Args:
            case_state: case.json 的程序状态快照

        Returns:
            RouteDecision: 包含路径 + 动作 + 文书模板 + 理由
        """
        # ── Step 0：基础校验 ──
        substantive_completeness = case_state.get("substantive_completeness", 0.0)
        if substantive_completeness < 0.70:
            return RouteDecision(
                route=ProsecutionRoute.NONE,
                action_required="PROVE_SUBSTANTIVE_CRIME_FIRST",
                target_template="",
                rationale=(
                    "实体构成要件完成度不足70%，暂时无法发起任何形式的刑事追责。\n"
                    "依据：2025意见第1-14条。请优先通过 trigger_checker.py 补齐逃债行为证据，"
                    "提升评分后再进入本决策树。"
                ),
                statutory_deadline=None,
                warnings=[
                    "⚠️ 追刑须以实体犯罪构成为前提，证据不足时强行自诉会被直接驳回"
                ]
            )

        # ── Step 1：读取当前程序状态 ──
        has_filed_police_report = case_state.get("has_filed_police_report", False)
        police_status = case_state.get("police_status", {})
        is_court_supportive = case_state.get("is_execution_court_supportive", False)
        days_since_filed = police_status.get("days_since_filed", 0)
        has_written_response = police_status.get("has_written_response", False)
        has_non_filing_notice = police_status.get("has_non_filing_notice", False)
        has_procurator_non_prosecution = police_status.get("has_procurator_non_prosecution", False)

        # ── Step 2：判断是否可以进入刑事自诉 ──
        if has_filed_police_report:
            # 条件①：拿到公安不予立案决定书
            if has_non_filing_notice:
                return self._route_private_prosecution(
                    reason="公安机关已出具《不予立案通知书》，符合2025意见第15条(一)前置条件",
                    template="拒不执行判决裁定罪刑事自诉状.docx",
                )

            # 条件②：检察院作出不起诉决定
            if has_procurator_non_prosecution:
                return self._route_private_prosecution(
                    reason="人民检察院已作出不起诉决定，符合2025意见第15条(二)前置条件",
                    template="拒不执行判决裁定罪刑事自诉状.docx",
                )

            # 条件③：公安接受控告材料后30日内未书面答复 ← 黄金突破口！
            if not has_written_response and days_since_filed > 30:
                return self._route_private_prosecution(
                    reason=(
                        f"公安机关接受控告材料已逾{days_since_filed}日未予书面答复，"
                        "符合2025意见第15条(三)法定前置条件！\n"
                        "原告（申请执行人）有权直接向执行法院提起刑事自诉，执行法院应当立案受理。"
                    ),
                    template="拒不执行判决裁定罪刑事自诉状.docx",
                )
            elif not has_written_response and 0 < days_since_filed <= 30:
                # 还在30天窗口期内，继续等
                remaining = 30 - days_since_filed
                return RouteDecision(
                    route=ProsecutionRoute.NONE,
                    action_required=f"WAIT_30DAY_WINDOW（还剩{remaining}天）",
                    target_template="",
                    rationale=(
                        f"公安机关已接受控告材料，当前为第{days_since_filed}天，"
                        f"尚在30天法定答复期限内。请等待至第31天再启动自诉。\n"
                        "⏰ 律师须在此期间保留好控告材料的投递凭证（快递单/回执）作为证据。"
                    ),
                    statutory_deadline=f"还剩{remaining}天（满30天后可启动自诉）",
                    warnings=[
                        "⚠️ 30天期限从递交控告材料之日起算（非公安机关签收之日起算）",
                        "⚠️ 建议使用EMS快递并保留签收凭证，精确计算起算日"
                    ]
                )

        # ── Step 3：判断法院移送路径 vs 公安自主控告 ──
        # 路径B：执行法院配合度高 → 提请法院移送公安
        if is_court_supportive:
            return RouteDecision(
                route=ProsecutionRoute.COURT_PUBLIC_TRANSFER,
                action_required="DRAFT_TRANSFER_APPLICATION",
                target_template="移送公安机关立案侦查申请书.docx",
                rationale=(
                    "执行法院配合度较高，建议优先向执行局提交《移送公安机关立案侦查申请书》。\n"
                    "依据：2025意见第3条（法院发现涉嫌拒执罪应移送公安机关）+ 第4条（执行机构收集犯罪线索后移交）。\n"
                    "由执行法院制作案件移送函，连同已掌握的证据材料一并移送公安机关立案侦查。\n"
                    "此路径可利用公权力进行强制侦查，降低原告取证成本，侦查效率远高于自诉。"
                ),
                statutory_deadline=None,
                warnings=[
                    "⚠️ 若法院拖延移送，可退而选择路径C（自行向公安控告）",
                    "⚠️ 法院移送≠公诉成功，公安立案后仍可能撤案或检察院不起诉"
                ]
            )

        # ── Step 4：起步路径：自行向公安机关控告 ──
        return RouteDecision(
            route=ProsecutionRoute.PUBLIC_REPORT_FIRST,
            action_required="DRAFT_POLICE_REPORT_BRIEF",
            target_template="刑事控告书_公安机关报案用.docx",
            rationale=(
                "目前尚未向公安机关报案，且执行法院未主动移送，无法直接启动自诉。\n"
                "依据：2025意见第12-14条。\n"
                "必须首先向执行法院所在地的公安机关（经侦部门）提交《刑事控告书》进行控告报案。\n"
                "⚠️ 此步骤为'自诉前置程序'的必经之路：\n"
                "① 公安接受材料后30日内不答复 → 自动激活自诉路径（路径A）\n"
                "② 公安出具不予立案通知 → 直接激活自诉路径（路径A）\n"
                "③ 检察院不起诉 → 直接激活自诉路径（路径A）"
            ),
            statutory_deadline="30天（从递交控告材料之日起算）",
            warnings=[
                "⚠️ 控告材料须使用EMS快递并保留签收凭证，精确起算30天期限",
                "⚠️ 建议同步向检察院申请立案监督（路径补充）",
                "⚠️ 公安控告后若出具不予立案通知，立即启动自诉，不要等待"
            ]
        )

    def _route_private_prosecution(self, reason: str, template: str) -> RouteDecision:
        """生成刑事自诉路径决策"""
        return RouteDecision(
            route=ProsecutionRoute.PRIVATE_PROSECUTION,
            action_required="DRAFT_PRIVATE_PROSECUTION_BRIEF",
            target_template=template,
            rationale=(
                f"【刑事自诉路径已解锁】\n{reason}\n\n"
                "依据：2025意见第15-18条。\n"
                "申请执行人作为自诉人，有权直接向执行法院提起刑事自诉，执行法院应当立案受理。\n"
                "下一步：立即起草《刑事自诉状》，向执行法院立案庭提交，同时申请财产保全/执行查封续封。"
            ),
            statutory_deadline=None,
            warnings=[
                "⚠️ 自诉状须附《不予立案通知书》或30天超期凭证原件",
                "⚠️ 自诉立案后须同步申请对被执行人采取强制措施（逮捕/取保候审）",
                "⚠️ 自诉审理期间，若发现新证据可申请检察院立案监督"
            ]
        )

    def get_statutory_deadline_reminder(self, route: ProsecutionRoute, police_filed_date: str = None) -> Optional[str]:
        """生成法定时限提醒文本"""
        if route == ProsecutionRoute.PUBLIC_REPORT_FIRST:
            return (
                "⏰ 【30天窗口期倒计时】\n"
                "从递交控告材料之日起算30天。\n"
                "第31天若公安未书面答复，立即启动刑事自诉。\n"
                "律师任务清单：\n"
                "  □ 今日通过EMS快递寄出控告材料（保留快递单）\n"
                "  □ 记录邮寄日期作为起算日\n"
                "  □ 快递签收后第28天开始关注公安答复\n"
                "  □ 若满30天未答复，准备自诉状"
            )
        elif route == ProsecutionRoute.PRIVATE_PROSECUTION and police_filed_date:
            dt = datetime.strptime(police_filed_date, "%Y-%m-%d")
            deadline = dt + timedelta(days=30)
            return f"⏰ 30天期限届满日：{deadline.strftime('%Y-%m-%d')}（届时未答复即可自诉）"
        return None


# ── CLI 调试入口 ──────────────────────────────────────────
if __name__ == "__main__":
    import json

    selector = RouteSelector()

    test_cases = [
        {
            "name": "起步：尚未报案",
            "state": {
                "substantive_completeness": 0.85,
                "has_filed_police_report": False,
                "is_execution_court_supportive": False,
            }
        },
        {
            "name": "公安超期30天未答复 → 自诉解锁",
            "state": {
                "substantive_completeness": 0.85,
                "has_filed_police_report": True,
                "police_status": {
                    "days_since_filed": 35,
                    "has_written_response": False,
                    "has_non_filing_notice": False,
                    "has_procurator_non_prosecution": False,
                },
                "is_execution_court_supportive": False,
            }
        },
        {
            "name": "公安已出具不予立案通知 → 自诉解锁",
            "state": {
                "substantive_completeness": 0.85,
                "has_filed_police_report": True,
                "police_status": {
                    "days_since_filed": 10,
                    "has_written_response": True,
                    "has_non_filing_notice": True,
                    "has_procurator_non_prosecution": False,
                },
                "is_execution_court_supportive": False,
            }
        },
        {
            "name": "法院配合度高 → 法院移送",
            "state": {
                "substantive_completeness": 0.85,
                "has_filed_police_report": False,
                "is_execution_court_supportive": True,
            }
        },
        {
            "name": "实体构成不足 → 阻断",
            "state": {
                "substantive_completeness": 0.45,
                "has_filed_police_report": False,
                "is_execution_court_supportive": False,
            }
        },
    ]

    for tc in test_cases:
        print(f"\n{'─'*60}")
        print(f"  测试案例：{tc['name']}")
        result = selector.determine_route(tc["state"])
        print(f"  路径：{result.route.value}")
        print(f"  动作：{result.action_required}")
        print(f"  文书：{result.target_template}")
        print(f"  理由：{result.rationale[:100]}...")
        if result.statutory_deadline:
            print(f"  时限：{result.statutory_deadline}")