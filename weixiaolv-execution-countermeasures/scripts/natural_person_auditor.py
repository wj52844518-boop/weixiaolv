#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自然人逃废债伎俩证据审查引擎 (Natural Person Evasion Auditor)
版本：V1.0 | 日期：2026-06-16
用途：对自然人债务人的10类逃废债套路进行系统性证据审查

调用方式（作为独立脚本）:
  python3 natural_person_auditor.py --case-id <ID> --debtor-type natural --evidence-dir <DIR>
  python3 natural_person_auditor.py --case-id <ID> --debtor-type natural --interactive

调用方式（作为模块）:
  from natural_person_auditor import NaturalPersonAuditor
  auditor = NaturalPersonAuditor(case_id="XXX", evidence_dir="/path/to/evidence")
  report = auditor.run_audit()
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

# ───────────────────────────────────────────────────────────────
#  10类自然人逃废债套路 × 证据审查协议（Evidence Protocol）
# ───────────────────────────────────────────────────────────────

@dataclass
class TacticEvidenceSpec:
    """单个套路的证据规格"""
    tactic_code: str          # N1 ~ N10
    tactic_name: str          # 套路中文名
    # 证据清单：[(证据名称, 证据用途, 红灯信号描述)]
    evidence_checklist: list
    # 红旗阈值（触发"高度可疑"的条件组合）
    red_flag_threshold: list  # list of str: 触发条件
    # 核心反击路径（RE→RO→RB 三段式）
    re_phase: str             # 确立我方本权
    ro_phase: str             # 定向击破权利障碍
    rb_phase: str             # 阻断被告之抗辩权
    # 对应法律路径
    legal_route: str          # 对应 countermeasure_matrix tactic_code
    # 补强证据方向
    reinforcement_directions: list


TACTIC_SPECS = {
    "N1": TacticEvidenceSpec(
        tactic_code="N1",
        tactic_name="假离婚析产",
        evidence_checklist=[
            ("离婚协议书", "证明财产分割比例严重偏颇", "90%以上财产归非债务人配偶"),
            ("离婚登记审查表", "证明离婚时间节点", "离婚发生在判决/执行前后1年内"),
            ("债务形成时间证据（借条/合同）", "证明债务在离婚前已形成", "债务形成时间早于离婚协议"),
            ("离婚后财产流向（银行流水）", "证明债务人账户大额异常转出", "离婚后有大额资金转至配偶账户"),
            ("不动产登记信息（历史）", "证明涉案房产查封前的权属状态", "离婚后房产仍由债务人实际占有"),
            ("物业费/水电费缴纳人", "证明实际居住人", "物业水电费由债务人支付"),
        ],
        red_flag_threshold=[
            "离婚时间节点接近判决/执行",
            "财产分割严重偏颇（>90%归配偶）",
            "离婚后债务人仍实际占有财产",
        ],
        re_phase="申请执行人的债权依据合法有效（生效判决/调解），债权发生在离婚协议签订之前。",
        ro_phase="离婚协议约定所有财产归配偶一方，债务人承担全部债务，属于民法典第538条规定的'无偿转让财产'行为，直接构成执行的权利障碍。",
        rb_phase="夫妻内部财产分割不适用善意取得，非债务人配偶不得以'善意取得'对抗申请执行人的强制执行请求权。",
        legal_route="TACTIC_NATURAL_DIVORCE",
        reinforcement_directions=[
            "调取债务人离婚前后的完整银行流水（律师调查令）",
            "调取配偶银行流水（证明资金最终回流）",
            "收集债务人仍实际占有涉案房产的物业缴费记录",
        ],
    ),

    "N2": TacticEvidenceSpec(
        tactic_code="N2",
        tactic_name="假买卖（低价/零价转让资产）",
        evidence_checklist=[
            ("买卖合同文本", "证明交易价格与签订时间", "成交价低于市场价70%或零对价"),
            ("不动产/车辆过户登记信息", "证明登记变更时间", "过户发生在诉讼/执行期间"),
            ("银行转账记录（买家）", "证明是否有真实资金支付", "无转账记录或资金即进即出"),
            ("卖方（被执行人）银行流水", "证明资金去向", "资金转入关联账户后立即转出"),
            ("交易对手身份信息", "证明与被执行人关系", "买方为近亲属或关联人"),
            ("不动产/车辆市场价值评估", "证明交易价格显著低于市场价", "成交价为市场价30%以下"),
            ("税费缴纳凭证（契税等）", "证明实际成交价与登记价不符", "税费金额与市场成交价严重背离"),
            ("物业费/水电费缴纳人", "证明实际占有情况", "过户后被执行人仍实际占有使用"),
        ],
        red_flag_threshold=[
            "低价或零对价成交",
            "无真实资金支付记录",
            "买方为近亲属或关联人",
            "交易时间在债务形成后/诉讼期间",
        ],
        re_phase="涉案不动产/车辆登记于被执行人名下，申请执行人依法享有查封、拍卖该财产的请求权。",
        ro_phase="被执行人与关联人恶意串通，签订虚假买卖合同，以明显不合理低价转让资产，符合民法典第538条'明显不合理的低价转让财产'构成要件，转让行为应予撤销。",
        rb_phase="关联人受让财产不构成善意取得（受让时知道或应当知道转让行为有害于债权人），不得以所有权抗辩执行。",
        legal_route="TACTIC_NATURAL_FAKE_SALE",
        reinforcement_directions=[
            "申请律师调查令调取买卖双方银行流水（证明无真实资金流）",
            "委托评估机构对涉案不动产/车辆进行市场价值评估",
            "收集被执行人实际占有使用该财产的证据（物业缴费、门禁记录等）",
        ],
    ),

    "N3": TacticEvidenceSpec(
        tactic_code="N3",
        tactic_name="假赠与（无偿转让资产）",
        evidence_checklist=[
            ("赠与合同/协议", "证明赠与时间与受赠人身份", "赠与发生在债务形成后"),
            ("不动产/股权/车辆过户登记材料", "证明赠与完成时间", "赠与后被执行人仍实际控制"),
            ("受赠人身份信息及与被执行人关系", "证明关联关系", "受赠人为近亲属或关联人"),
            ("赠与撤销条件核查", "证明赠与是否完成公证/交付", "未公证+未交付→可主张撤销赠与"),
            ("被执行人银行流水", "证明资产来源与资金去向", "资产由被执行人出资但登记在受赠人名下"),
            ("实际占有证据（物业/车辆使用）", "证明被执行人仍实际控制", "赠与后财产由被执行人持续占有使用"),
        ],
        red_flag_threshold=[
            "赠与发生在债务形成之后",
            "受赠人为近亲属或关联人",
            "被执行人赠与后仍实际占有使用该财产",
            "无合理对价关系",
        ],
        re_phase="涉案财产系被执行人出资购买后无偿赠与，受赠人未支付任何对价，申请执行人依法对被执行人名下及等价财产享有执行请求权。",
        ro_phase="赠与行为发生在债务形成后，实质是无偿转让财产以规避执行，符合民法典第538条'无偿转让财产'的撤销要件。",
        rb_phase="受赠人无偿取得财产，不符合善意取得的'支付合理对价'要件，不能对抗债权人的撤销权。",
        legal_route="TACTIC_NATURAL_FAKE_DONATION",
        reinforcement_directions=[
            "调取被执行人出资购买资产的银行流水（律师调查令）",
            "调查受赠人与被执行人的社会关系及资金往来",
            "收集被执行人实际占有使用该财产的持续证据",
        ],
    ),

    "N4": TacticEvidenceSpec(
        tactic_code="N4",
        tactic_name="财产代持（登记在他人名下）",
        evidence_checklist=[
            ("代持协议/微信记录/录音", "证明代持关系存在", "无书面协议但有资金往来印证"),
            ("实际出资银行流水", "证明资产实际由谁出资", "首付款/按揭款全部由债务人账户支付"),
            ("不动产购买合同/发票", "证明购买资金来源", "购房款由债务人支付但登记在代持人名下"),
            ("物业费/燃气/宽带开通人信息", "证明实际控制人", "开通人均为债务人"),
            ("车辆保险投保人/保养记录", "证明实际控制人", "保险投保人为债务人"),
            ("代持人与债务人关系证据", "证明存在密切人身/经济关系", "代持人为配偶/父母/子女/员工"),
            ("社保/工资发放记录", "证明劳动关系", "代持人为债务人公司员工但无正常工资"),
            ("资产取得时间 vs 债务形成时间", "证明时间线异常", "资产在债务形成后短期内完成代持化"),
        ],
        red_flag_threshold=[
            "债务人是实际出资人但资产登记在他人名下",
            "代持人与债务人有密切人身关系",
            "代持人无正常出资能力证明",
            "债务人仍实际控制使用该财产",
        ],
        re_phase="不动产/车辆虽登记在代持人名下，但实际出资人为被执行人，依据民法典第209条'不动产物权登记的推定效力'可被相反证据推翻，请求确认被执行人为实际所有权人。",
        ro_phase="代持关系系双方真实意思表示，被执行人作为实际出资人享有实质所有权，代持人仅为名义登记人，不能以物权公示对抗申请执行人的强制执行请求权。",
        rb_phase="代持人主张所有权系其独立物权，但无实际出资证明，不能满足善意取得的'合理对价+合法占有'要件，代持抗辩不能成立。",
        legal_route="TACTIC_NATURAL_ASSET_HOLDING",
        reinforcement_directions=[
            "申请律师调查令查询债务人银行流水（证明实际出资）",
            "向物业公司/燃气公司/宽带运营商查询实际开户人信息",
            "委托调查公司收集债务人实际控制使用该财产的证据（照片/视频/出入记录）",
            "调取车辆保险单及理赔记录（证明投保人和实际使用人）",
        ],
    ),

    "N5": TacticEvidenceSpec(
        tactic_code="N5",
        tactic_name="虚假诉讼保护（首封+以物抵债）",
        evidence_checklist=[
            ("虚假诉讼的判决/调解/仲裁文书", "证明存在关联诉讼", "调解结案/缺席判决/无实质对抗"),
            ("款项支付凭证（原告主张的债权）", "证明债权是否真实支付", "无真实款项支付或资金循环转账"),
            ("借款合同/借条", "证明债权形成时间", "债权形成时间在被执行人被我方起诉之后"),
            ("查封/抵押登记时间线", "证明查封时间节点", "关联诉讼的查封早于/同步于我方诉讼保全"),
            ("关联案件工商/户籍信息", "证明原告与被告的关联关系", "原告与被告存在亲属/商业合作关系"),
            ("以物抵债裁定及评估报告", "证明抵债价格是否合理", "以物抵债价格显著低于评估价"),
            ("被执行人银行流水（收付款账户）", "证明资金是否真实流转", "资金到账后立即转回或提现"),
            ("关联案件庭审笔录", "证明是否有实质对抗", "双方无实质抗辩，疑似串通"),
        ],
        red_flag_threshold=[
            "关联诉讼以调解或缺席判决结案",
            "无真实款项支付，资金循环转账",
            "债权形成时间在被执行人被我方起诉之后",
            "以物抵债价格显著低于评估价",
        ],
        re_phase="申请执行人依据生效法律文书对被执行人名下财产享有强制执行请求权，该权利优先于被执行人与关联人虚构债权产生的'抵押权'。",
        ro_phase="关联诉讼系被执行人与案外人恶意串通，以虚假诉讼方式转移资产，符合刑法第307条之一虚假诉讼罪构成要件；同时依据民法典第538条，该转让行为应予撤销。",
        rb_phase="虚假诉讼中的'债权人'不享有真实债权，其对涉案财产的'抵押权'系虚构，不具有排除执行的效力。",
        legal_route="TACTIC_NATURAL_FAKE_DEBT_MORTGAGE",
        reinforcement_directions=[
            "向法院调取关联案件的庭审笔录（证明双方无实质对抗）",
            "申请审计机构对被执行人及关联人银行流水进行专项审计",
            "收集被执行人与'原告'之间的通讯记录/资金往来（证明恶意串通）",
            "向检察院申请启动虚假诉讼监督程序",
        ],
    ),

    "N6": TacticEvidenceSpec(
        tactic_code="N6",
        tactic_name="虚构债务设定抵押",
        evidence_checklist=[
            ("借款合同/借条/转账记录", "证明主债务是否真实", "无真实转账记录或资金即进即出"),
            ("不动产/股权抵押登记证明", "证明抵押登记时间", "抵押登记发生在债务形成后/判决后"),
            ("抵押权人身份及与被执行人关系", "证明是否存在关联关系", "抵押权人为近亲属或关联人"),
            ("债务金额与抵押物价值对比", "证明是否合理", "债务金额与抵押物价值严重不匹配"),
            ("抵押权人银行流水", "证明是否真实支付", "无资金支付或资金绕一圈后回转"),
            ("被执行人银行流水", "证明资金最终去向", "资金到账后立即转至关联账户"),
            ("抵押注销/执行情况", "证明抵押是否被实际主张", "抵押从未被实际主张，疑似工具性抵押"),
        ],
        red_flag_threshold=[
            "主债务无真实转账记录",
            "抵押登记发生在债务形成后",
            "抵押权人为近亲属或关联人",
            "债务金额与抵押物价值严重不匹配",
        ],
        re_phase="申请执行人依据生效法律文书对被执行人名下财产享有执行请求权，该权利不因被执行人其后设定虚假抵押权而受影响。",
        ro_phase="被执行人与抵押权人恶意串通，虚构债务并设定抵押权，意图排除申请执行人的强制执行，属于民法典第538条'恶意延长其到期债权的履行期限'的行为，依法应予撤销。",
        rb_phase="虚构债务的抵押权不具有真实性，抵押权人不得以抵押权对抗申请执行人的执行请求权。",
        legal_route="TACTIC_NATURAL_FAKE_DEBT_MORTGAGE",
        reinforcement_directions=[
            "申请律师调查令查询抵押权人银行流水（证明无真实放款）",
            "调取抵押权人与被执行人之间的全部资金往来记录",
            "委托评估机构对抵押物进行价值评估（证明价值严重高估）",
            "向法院申请确认抵押合同无效之诉",
        ],
    ),

    "N7": TacticEvidenceSpec(
        tactic_code="N7",
        tactic_name="虚构长期租赁关系",
        evidence_checklist=[
            ("租赁合同文本及签订日期", "证明租赁开始时间", "合同签订时间在查封之后"),
            ("租金支付银行转账记录", "证明是否有真实租金支付", "无转账记录或一次性支付但无资金流"),
            ("物业费缴纳人信息", "证明实际占有使用人", "物业费由被执行人（出租人）缴纳"),
            ("水电费户名及缴纳记录", "证明实际使用情况", "水电费户名仍为被执行人"),
            ("租赁备案登记信息", "证明备案时间", "未备案或备案时间晚于查封"),
            ("被执行人与承租人关系证据", "证明是否存在关联关系", "承租人为近亲属或关联人"),
            ("承租人实际占有证据（装修记录/营业执照注册地址）", "证明是否实际占有", "涉案不动产由被执行人占有使用，承租人从未实际占有"),
            ("租金市场价格对比", "证明租金是否合理", "租金显著低于市场价"),
        ],
        red_flag_threshold=[
            "租赁合同签订时间在查封之后",
            "无真实租金支付记录",
            "涉案不动产仍由被执行人实际占有使用",
            "承租人为近亲属或关联人",
        ],
        re_phase="依据民法典第725条，'买卖不破租赁'的适用前提是承租人在租赁物被查封前已合法占有涉案不动产。申请执行人请求法院依法涤除该租赁权后进行拍卖。",
        ro_phase="经查，涉案不动产的物业费、水电费均由被执行人缴纳，承租人从未实际占有使用，租赁关系系虚构。依据民法典第725条，'买卖不破租赁'的法定前提不成立，该租赁权不能阻却执行。",
        rb_phase="即便承租人主张租赁权，因其未能证明在查封前已合法占有涉案不动产，不符合'买卖不破租赁'的法定构成要件，抗辩权不能成立。",
        legal_route="TACTIC_NATURAL_FAKE_LEASE",
        reinforcement_directions=[
            "向物业公司调取物业费缴纳记录（证明被执行人为实际缴费人）",
            "向电力公司/自来水公司/燃气公司调取户名及使用记录",
            "收集被执行人实际占有使用涉案不动产的证据（照片/视频/邻居证言）",
            "调查承租人是否有其他实际经营/居住地址证明",
        ],
    ),

    "N8": TacticEvidenceSpec(
        tactic_code="N8",
        tactic_name="案外人执行异议阻挡",
        evidence_checklist=[
            ("案外人执行异议申请书", "证明异议类型和理由", "案外人主张所有权/租赁权/抵押权等"),
            ("基础法律关系证明（买卖/租赁/借贷协议）", "证明基础法律关系是否真实", "存在N2/N3/N7所列虚假法律关系特征"),
            ("异议申请时间 vs 查封时间", "证明时间节点是否异常", "异议发生在执行程序启动后，疑似恶意阻却"),
            ("案外人与被执行人关系证据", "证明是否存在关联关系", "案外人与被执行人存在亲属/商业关联"),
            ("案外人实际占有证据", "证明是否满足占有要件", "无法提供充分实际占有证据"),
            ("案外人付款凭证", "证明是否支付合理对价", "无法提供银行转账记录或资金来源不明"),
        ],
        red_flag_threshold=[
            "案外人与被执行人存在关联关系",
            "基础法律关系存在N2/N3/N7所列虚假特征",
            "案外人无法证明在查封前已合法占有",
            "异议时间节点异常（拍卖公告后立即提起）",
        ],
        re_phase="申请执行人依据生效法律文书对涉案财产享有执行请求权，该权利优先于案外人的实体权利主张。",
        ro_phase="案外人与被执行人恶意串通，虚构买卖/租赁等法律关系，意图阻却执行程序。依据民法典第725条，'买卖不破租赁'须以查封前已合法占有为前提；依据民法典第235条，所有权返还请求权须证明合法取得。案外人的异议请求缺乏事实和法律依据。",
        rb_phase="案外人援引所有权或租赁权排除执行，但其不能证明：①支付了合理对价；②在查封前已合法占有涉案财产。上述抗辩权均不能成立。",
        legal_route="TACTIC_NATURAL_FAKE_LEASE",
        reinforcement_directions=[
            "对案外人的基础法律关系进行专项审查（套用N2/N3/N7审查标准）",
            "收集案外人与被执行人恶意串通的证据（通讯记录/资金往来）",
            "申请法院对案外人实际占有情况进行现场调查",
            "准备质证意见，对案外人的证据逐项驳斥",
        ],
    ),

    "N9": TacticEvidenceSpec(
        tactic_code="N9",
        tactic_name="双户口/多护照/资产分散",
        evidence_checklist=[
            ("公安机关户籍信息查询结果", "证明是否存在两个有效户口", "存在两个有效户口，或一个注销一个保留"),
            ("出入境管理局护照信息", "证明持有的护照数量和号码", "持有多个有效护照"),
            ("不动产登记信息（多省份）", "证明资产分布情况", "资产分散在不同身份名下"),
            ("银行账户开户信息（各银行）", "证明账户分布情况", "账户开立在多个不同身份下"),
            ("社会保险缴费记录", "证明实际投保人身份", "社保由债务人工作单位缴纳但对应另一身份"),
            ("生物特征/指纹/照片比对", "证明不同户口是否为同一生物个体", "不同户口但照片相同或指纹一致"),
            ("婚姻登记信息（含配偶）", "证明是否存在利用配偶身份分散资产", "婚后财产大量登记在配偶名下且价值异常"),
            ("被执行人所有身份信息的关联性分析", "证明多个身份是否为同一人控制", "多个身份的资产/账户存在资金往来"),
        ],
        red_flag_threshold=[
            "存在两个或以上有效户口/护照",
            "资产分散在多个身份名下",
            "不同身份之间存在资金往来",
            "生物特征显示多个身份为同一人",
        ],
        re_phase="不同身份证号/姓名下的资产实际均为同一自然人所有，该自然人系生效法律文书确定的被执行人，依法对其全部资产享有执行请求权。",
        ro_phase="依据《居民身份证法》第16条及《护照法》第16条，一个自然人不得持有两个有效身份证明。公安机关已出具'同人异名证明'证实多个身份为同一人，其名下全部资产依法应合并执行。",
        rb_phase="被执行人利用多个身份分散资产的行为不改变其为同一法律主体的本质，不能以'资产登记在不同身份名下'为由对抗执行。",
        legal_route="TACTIC_NATURAL_DUAL_HOUSEHOLD",
        reinforcement_directions=[
            "向公安局申请出具'同人异名证明'（证明多个身份证号为同一生物个体）",
            "向多省份不动产登记中心申请查询（持法院调查令）",
            "向各银行申请查询被执行人及配偶的账户信息",
            "向出入境管理局查询全部护照信息及出入境记录",
            "申请追加/变更'第二身份'为被执行人，将名下资产合并执行",
        ],
    ),

    "N10": TacticEvidenceSpec(
        tactic_code="N10",
        tactic_name="勾兑/干扰执行",
        evidence_checklist=[
            ("执行异议申请书（历次）", "证明异议提起频率和理由", "反复提起异议，每次理由不同但均被驳回"),
            ("异议提起时间 vs 执行进度记录", "证明时间节点是否异常", "每次拍卖公告后即提起异议，时间节点异常精准"),
            ("执行和解协议及履行情况", "证明和解是否真实履行", "和解后未履行但未受处罚，疑似虚假和解"),
            ("通话记录/短信/微信记录（执行人员）", "证明是否存在不正当接触", "与执行人员存在异常通讯记录"),
            ("关联案件分析报告", "证明是否存在类似异常行为模式", "关联案件中存在类似反复异议/虚假和解行为"),
            ("执行人员回避申请记录", "证明是否曾申请回避", "当事人曾申请执行人员回避但被驳回"),
            ("执行笔录/送达回证时间记录", "证明执行程序是否正常推进", "执行推进在某些节点异常缓慢，疑似人为干预"),
        ],
        red_flag_threshold=[
            "反复提起执行异议，每次理由不同但均被驳回",
            "拍卖公告后精准时间节点提起异议",
            "和解后不履行但未受罚款/拘留等强制措施",
            "存在与执行人员不正当接触的通讯记录",
        ],
        re_phase="申请执行人依据生效法律文书享有强制执行请求权，被执行人通过反复滥用执行异议程序拖延、阻挠执行，严重损害了申请执行人的合法权益。",
        ro_phase="被执行人的行为符合《民事诉讼法》规定的'恶意拖延执行'情形，执行法院应当依法对其采取罚款、拘留等强制措施；情节严重的，依据刑法第313条追究拒执罪刑事责任。",
        rb_phase="即便被执行人提出程序性异议，其异议已被全部驳回，不能以此为由继续阻却执行。申请执行人同时保留对执行人员涉嫌违纪违法的举报权利。",
        legal_route="TACTIC_NATURAL_DELAY",
        reinforcement_directions=[
            "整理历次异议被驳回的裁定书（证明异议被反复驳回）",
            "收集拍卖公告后精准时间提起异议的证据（证明恶意拖延）",
            "整理和解协议及履行情况（证明虚假和解）",
            "向同级人民检察院举报执行人员涉嫌违纪违法（刑法§399条徇私枉法罪）",
            "申请上级法院执行监督（民诉法第232条）",
        ],
    ),
}


# ───────────────────────────────────────────────────────────────
#  审查报告核心数据模型
# ───────────────────────────────────────────────────────────────

@dataclass
class TacticAuditResult:
    """单个套路审查结果"""
    tactic_code: str
    tactic_name: str
    status: str              # CONFIRMED / SUSPECTED / RULED_OUT / UNCHECKED
    evidence_strength: str    # HIGH / MEDIUM / LOW
    triggered_red_flags: list
    key_evidence_obtained: list
    evidence_gaps: list
    countermeasure_plan: str
    three_stage_rebuttal: dict  # {"RE": ..., "RO": ..., "RB": ...}
    confidence: float        # 0.0 ~ 1.0


@dataclass
class AuditReport:
    """完整审查报告"""
    case_id: str
    debtor_name: str
    debtor_type: str = "natural_person"
    audit_date: str = ""
    overall_assessment: str = ""   # 总体评估
    identified_tactics: list = field(default_factory=list)
    priority_targets: list = field(default_factory=list)  # 按证据充分度排序
    next_steps: list = field(default_factory=list)
    minimum_evidence_package_missing: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ───────────────────────────────────────────────────────────────
#  核心审查引擎
# ───────────────────────────────────────────────────────────────

class NaturalPersonAuditor:
    """
    自然人逃废债伎俩证据审查引擎
    用法：
      auditor = NaturalPersonAuditor(case_id="XXX", evidence_dir="/path/to/evidence")
      report = auditor.run_audit()
    """

    TACTIC_CODES = list(TACTIC_SPECS.keys())  # ["N1".."N10"]

    def __init__(self, case_id: str, evidence_dir: Optional[str] = None,
                 debtor_name: str = "未知债务人"):
        self.case_id = case_id
        self.debtor_name = debtor_name
        self.evidence_dir = evidence_dir
        self.audit_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._evidence_cache = {}
        if evidence_dir:
            self._load_evidence(evidence_dir)

    def _load_evidence(self, evidence_dir: str):
        """惰性载入证据目录下的文件，构建证据缓存"""
        if not os.path.isdir(evidence_dir):
            return
        for fname in os.listdir(evidence_dir):
            fpath = os.path.join(evidence_dir, fname)
            if os.path.isfile(fpath):
                # 按文件名关键词分类缓存
                fname_lower = fname.lower()
                for code in self.TACTIC_CODES:
                    if code.lower() in fname_lower:
                        self._evidence_cache.setdefault(code, []).append(fpath)
                        break

    def audit_tactic(self, tactic_code: str,
                     user_evidence_inputs: Optional[dict] = None) -> TacticAuditResult:
        """
        对单个套路进行证据审查。

        user_evidence_inputs 格式:
          {
            "N1": {
              "离婚协议书": True,           # 已提供
              "离婚登记审查表": True,
              "债务形成时间证据": False,    # 未提供
              ...
            },
            "N4": { ... }
          }
        """
        spec = TACTIC_SPECS.get(tactic_code)
        if not spec:
            raise ValueError(f"Unknown tactic_code: {tactic_code}")

        # 用户输入证据状态（默认全部 UNCHECKED）
        evidence_status = user_evidence_inputs.get(tactic_code, {}) if user_evidence_inputs else {}

        # 1. 计算触发的红灯信号
        triggered = []
        for flag in spec.red_flag_threshold:
            # 若用户提供了对应证据且为"已获取"状态，该红灯信号得到证据支撑
            # 注意：这里需要建立红灯信号→证据项的映射，此处做简化处理
            triggered.append(flag)

        # 2. 已获取的证据 vs 缺失证据
        obtained = []
        gaps = []
        for ev_name, ev_use, red_signal in spec.evidence_checklist:
            if evidence_status.get(ev_name, False):
                obtained.append(f"{ev_name}（用途：{ev_use}）")
            else:
                gaps.append(f"{ev_name}（用途：{ev_use}）")

        # 3. 红灯阈值命中数
        hit_count = sum(1 for flag in spec.red_flag_threshold
                        if any(ev in str(evidence_status) for ev in ["True", "true"]))

        # 4. 判定 status
        obtained_count = sum(1 for v in evidence_status.values() if v)
        total_count = len(spec.evidence_checklist)
        coverage = obtained_count / total_count if total_count > 0 else 0

        if obtained_count == 0:
            status = "UNCHECKED"
            strength = "LOW"
            confidence = 0.0
        elif hit_count >= 2 and coverage >= 0.4:
            status = "CONFIRMED"
            strength = "HIGH" if hit_count >= 3 else "MEDIUM"
            confidence = 0.85 if strength == "HIGH" else 0.70
        elif hit_count >= 1 or coverage >= 0.25:
            status = "SUSPECTED"
            strength = "MEDIUM" if coverage >= 0.4 else "LOW"
            confidence = 0.50
        else:
            status = "RULED_OUT"
            strength = "LOW"
            confidence = 0.15

        # 5. 补强方向过滤（只保留证据缺口项）
        reinforcement = [d for d in spec.reinforcement_directions
                          if any(g in d for g in [e.split("（")[0] for e in gaps])]

        return TacticAuditResult(
            tactic_code=tactic_code,
            tactic_name=spec.tactic_name,
            status=status,
            evidence_strength=strength,
            triggered_red_flags=triggered[:],
            key_evidence_obtained=obtained,
            evidence_gaps=gaps,
            countermeasure_plan=spec.legal_route,
            three_stage_rebuttal={
                "RE": spec.re_phase,
                "RO": spec.ro_phase,
                "RB": spec.rb_phase,
            },
            confidence=confidence,
        )

    def run_audit(self,
                  user_evidence_inputs: Optional[dict] = None,
                  confirmed_only: bool = False) -> AuditReport:
        """
        运行全量审查。

        user_evidence_inputs 格式：
          {
            "N1": {"证据名": True/False, ...},
            ...
          }
        confirmed_only: True → 只输出 CONFIRMED/SUSPECTED 的套路
        """
        results = []
        for code in self.TACTIC_CODES:
            result = self.audit_tactic(code, user_evidence_inputs)
            if confirmed_only and result.status in ("RULED_OUT", "UNCHECKED"):
                continue
            results.append(result)

        # 按 confidence 降序排列（优先处理高确信度套路）
        results.sort(key=lambda x: x.confidence, reverse=True)

        # 优先突破目标（仅 CONFIRMED + HIGH）
        priority = [r.tactic_code for r in results
                    if r.status == "CONFIRMED" and r.evidence_strength == "HIGH"]

        # 总体评估
        confirmed_count = sum(1 for r in results if r.status == "CONFIRMED")
        suspected_count = sum(1 for r in results if r.status == "SUSPECTED")
        if confirmed_count >= 2:
            overall = "高度可疑——已确认2种以上逃废债伎俩，建议立即启动反击"
        elif confirmed_count == 1:
            overall = "中度可疑——已确认1种逃废债伎俩，需补强证据后启动反击"
        elif suspected_count >= 3:
            overall = "中度可疑——存在多种疑似伎俩，需进一步调查"
        elif suspected_count >= 1:
            overall = "待观察——存在疑似伎俩，需补充关键证据"
        else:
            overall = "暂无明显逃废债迹象——持续监控"

        # 下一步动作（汇总）
        next_steps = []
        for r in results:
            if r.status in ("CONFIRMED", "SUSPECTED") and r.evidence_gaps:
                next_steps.append(
                    f"N{r.tactic_code[1:]} {r.tactic_name}：补充证据 {r.evidence_gaps[0].split('（')[0]}"
                )

        report = AuditReport(
            case_id=self.case_id,
            debtor_name=self.debtor_name,
            debtor_type="natural_person",
            audit_date=self.audit_date,
            overall_assessment=overall,
            identified_tactics=[asdict(r) for r in results],
            priority_targets=priority,
            next_steps=next_steps,
        )
        return report

    def print_report(self, report: AuditReport):
        """格式化打印审查报告"""
        print(f"\n{'='*60}")
        print(f"  自然人逃废债伎俩识别与反制报告")
        print(f"{'='*60}")
        print(f"  案件编号：{report.case_id}")
        print(f"  债务人：{report.debtor_name}")
        print(f"  审核日期：{report.audit_date}")
        print(f"{'─'*60}")
        print(f"  【总体评估】{report.overall_assessment}")
        print(f"{'─'*60}")

        for t in report.identified_tactics:
            status_icon = {"CONFIRMED": "🔴", "SUSPECTED": "🟡",
                           "RULED_OUT": "⚪", "UNCHECKED": "⬜"}.get(t["status"], "⚪")
            print(f"\n  {status_icon} [{t['tactic_code']}] {t['tactic_name']}")
            print(f"     状态：{t['status']} | 证据强度：{t['evidence_strength']} | 置信度：{t['confidence']:.0%}")

            if t["key_evidence_obtained"]:
                print(f"     ✅ 已获取证据：")
                for e in t["key_evidence_obtained"]:
                    print(f"        • {e}")
            if t["evidence_gaps"]:
                print(f"     ❌ 证据缺口：")
                for g in t["evidence_gaps"]:
                    print(f"        • {g}")

            if t["status"] in ("CONFIRMED", "SUSPECTED"):
                rebut = t["three_stage_rebuttal"]
                print(f"     ⚡ 三段式反击：")
                print(f"        RE：{rebut['RE'][:50]}...")
                print(f"        RO：{rebut['RO'][:50]}...")
                print(f"        RB：{rebut['RB'][:50]}...")

        if report.priority_targets:
            print(f"\n{'─'*60}")
            print(f"  【优先突破目标】")
            for pt in report.priority_targets:
                print(f"     🔴 {pt}")

        if report.next_steps:
            print(f"\n{'─'*60}")
            print(f"  【下一步核查动作】")
            for i, ns in enumerate(report.next_steps[:5], 1):
                print(f"     {i}. {ns}")

        print(f"\n{'='*60}\n")


# ───────────────────────────────────────────────────────────────
#  CLI 入口
# ───────────────────────────────────────────────────────────────

def build_interactive_prompts() -> dict:
    """
    构建交互式证据输入模板（N1-N10 × 每套路6-8个证据项）
    返回格式：{"N1": {"证据名": False, ...}, ...}
    """
    import copy
    prompts = {}
    for code, spec in TACTIC_SPECS.items():
        prompts[code] = {ev[0]: False for ev in spec.evidence_checklist}
    return prompts


def interactive_mode(case_id: str, debtor_name: str):
    """交互式证据录入模式"""
    print(f"\n{'='*60}")
    print(f"  自然人逃废债伎俩证据审查 - 交互式录入")
    print(f"  案件：{case_id} | 债务人：{debtor_name}")
    print(f"{'='*60}\n")

    evidence_inputs = {}
    for code in TACTIC_SPECS.keys():
        spec = TACTIC_SPECS[code]
        print(f"\n【{code}】{spec.tactic_name}")
        evidence_inputs[code] = {}
        for ev_name, ev_use, _ in spec.evidence_checklist:
            while True:
                ans = input(f"  {ev_name}（用途：{ev_use}）[y/n]: ").strip().lower()
                if ans in ("y", "yes"):
                    evidence_inputs[code][ev_name] = True
                    break
                elif ans in ("n", "no"):
                    evidence_inputs[code][ev_name] = False
                    break
                else:
                    print("  请输入 y 或 n")

    return evidence_inputs


def main():
    parser = argparse.ArgumentParser(
        description="自然人逃废债伎俩证据审查引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--case-id", default="UNKNOWN", help="案件编号")
    parser.add_argument("--debtor-name", default="未知债务人", help="债务人姓名")
    parser.add_argument("--debtor-type", default="natural",
                        choices=["natural", "corp"],
                        help="债务人类型（natural=自然人，corp=法人）")
    parser.add_argument("--evidence-dir", default=None,
                        help="证据目录路径（可选）")
    parser.add_argument("--interactive", action="store_true",
                        help="启动交互式证据录入")
    parser.add_argument("--json-output", action="store_true",
                        help="输出JSON格式报告")
    parser.add_argument("--confirmed-only", action="store_true",
                        help="仅输出确认/疑似的套路")

    args = parser.parse_args()

    if args.debtor_type != "natural":
        print("⚠️  当前仅支持自然人（N1-N10）。法人套路请使用 execution-countermeasures 主模块。")
        sys.exit(1)

    # 交互式录入
    if args.interactive:
        evidence_inputs = interactive_mode(args.case_id, args.debtor_name)
    else:
        evidence_inputs = None

    # 运行审查
    auditor = NaturalPersonAuditor(
        case_id=args.case_id,
        debtor_name=args.debtor_name,
        evidence_dir=args.evidence_dir,
    )
    report = auditor.run_audit(
        user_evidence_inputs=evidence_inputs,
        confirmed_only=args.confirmed_only,
    )

    # 输出
    if args.json_output:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        auditor.print_report(report)


if __name__ == "__main__":
    main()
