#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
营利法人逃废债伎俩证据审查引擎 (Legal Entity Evasion Auditor)
版本：V1.0 | 日期：2026-06-16
用途：对营利法人债务人（含公司、企业）的逃废债套路进行系统性证据审查

调用方式（作为独立脚本）:
  python3 legal_entity_auditor.py --case-id <ID> --debtor-name <NAME> --interactive
  python3 legal_entity_auditor.py --case-id <ID> --debtor-name <NAME> --json-output

调用方式（作为模块）:
  from legal_entity_auditor import LegalEntityAuditor
  auditor = LegalEntityAuditor(case_id="XXX", debtor_name="某公司")
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
#  营利法人逃废债 16 类套路 × 证据审查协议（Evidence Protocol）
# ───────────────────────────────────────────────────────────────

@dataclass
class CorpTacticEvidenceSpec:
    """单个法人套路的证据规格"""
    tactic_code: str          # C1 ~ C16
    tactic_name: str          # 套路中文名
    evidence_checklist: list  # [(证据名称, 证据用途, 红灯信号)]
    red_flag_threshold: list  # 触发"高度可疑"的条件组合
    re_phase: str             # RE：三段式第一阶段
    ro_phase: str             # RO：三段式第二阶段
    rb_phase: str             # RB：三段式第三阶段
    legal_route: str           # 对应 countermeasure_matrix tactic_code
    reinforcement_directions: list  # 补强证据方向


TACTIC_SPECS = {
    "C1": CorpTacticEvidenceSpec(
        tactic_code="C1",
        tactic_name="资产虚假转移（判决/执行期间零对价/低价转让）",
        evidence_checklist=[
            ("股权转让合同/资产转让协议", "证明转让时间、交易价格、交易对手", "零对价或低于市场价70%"),
            ("工商变更登记信息", "证明股权/资产过户完成时间", "发生在诉讼期间或执行期间"),
            ("转让方（被执行人）银行流水", "证明资金去向", "资金转入关联账户后立即转出"),
            ("受让方身份信息及与被执行人关系", "证明是否存在关联关系", "受让方为关联方或近亲属"),
            ("标的资产市场价值评估报告", "证明交易价格是否合理", "成交价为市场价30%以下"),
            ("受让方银行转账记录", "证明是否有真实资金支付", "无转账记录或资金即进即出"),
            ("税款缴纳凭证", "证明实际成交价与登记价是否一致", "税费金额与登记交易价严重背离"),
        ],
        red_flag_threshold=[
            "零对价或低价转让",
            "发生在诉讼/执行期间",
            "受让方为关联方或近亲属",
            "无真实资金支付",
        ],
        re_phase="申请执行人依据生效法律文书对被执行人名下财产享有强制执行请求权，被执行人在诉讼/执行期间转让资产的行为直接削弱了执行能力。",
        ro_phase="被执行人与受让方恶意串通，以明显不合理低价转让资产，符合民法典第539条'明显不合理低价转让财产'的撤销要件，转让行为应予撤销。",
        rb_phase="受让方不能证明其为善意第三人（受让时知道或应当知道转让行为有害于债权人），不得以所有权抗辩执行。",
        legal_route="TACTIC_CORP_SHELL_TRANSFER",
        reinforcement_directions=[
            "申请律师调查令调取转让双方银行流水（证明无真实资金流）",
            "委托评估机构对涉案资产进行市场价值评估",
            "调查受让方与被执行人的工商关联/股权关联/人员关联",
            "收集被执行人在转让后仍实际控制使用该资产的证据",
        ],
    ),

    "C2": CorpTacticEvidenceSpec(
        tactic_code="C2",
        tactic_name="财产代持（挂在会计/股东/股东配偶/员工账户）",
        evidence_checklist=[
            ("代持协议/股权代持合同/借名协议", "证明代持关系存在", "无书面协议但有资金往来印证"),
            ("实际出资银行流水（公司账户或个人账户）", "证明资产实际由谁出资", "首付款/按揭款由被执行人账户支付"),
            ("资产购买合同/发票/付款凭证", "证明购买资金来源", "购房款/购车款由被执行人支付但登记在代持人名下"),
            ("银行回单/转账凭证", "证明资金流转路径", "资金从被执行人账户流向代持人，再流向出售方"),
            ("代持人与被执行人关系证据（工商/户籍/社保）", "证明是否存在关联关系", "代持人为股东/会计/配偶/员工"),
            ("代持人银行流水", "证明代持人是否有独立出资能力", "代持人账户无正常收入/经营流水"),
            ("代持资产的实际控制证据（物业缴费/车辆保险）", "证明实际控制人", "保险投保人/物业缴费人为被执行人"),
        ],
        red_flag_threshold=[
            "被执行人为实际出资人但资产登记在他人名下",
            "代持人与被执行人有密切人身/经济关系",
            "代持人无独立出资能力证明",
            "被执行人仍实际控制使用该财产",
        ],
        re_phase="涉案财产虽登记在代持人名下，但实际出资人为被执行人公司，依据民法典第209条'不动产物权登记的推定效力'可被相反证据推翻。",
        ro_phase="被执行人通过代持人持有资产，意图规避执行。代持关系不能对抗申请执行人的强制执行请求权。",
        rb_phase="代持人不能证明其有独立出资，不能满足善意取得的'合理对价+合法占有'要件，代持抗辩不能成立。",
        legal_route="TACTIC_CORP_FUND_HIDING",
        reinforcement_directions=[
            "申请律师调查令查询被执行人及代持人银行流水（资金穿透）",
            "向物业公司/燃气公司查询实际开户人和缴费人",
            "调查代持人的职业、收入、社保缴纳情况（证明无出资能力）",
            "收集被执行人实际控制使用该财产的证据（照片/视频/出入记录）",
        ],
    ),

    "C3": CorpTacticEvidenceSpec(
        tactic_code="C3",
        tactic_name="自有财产不办理相关凭证（资产权属凭证缺失）",
        evidence_checklist=[
            ("不动产权属证书/车辆登记证书", "证明权属凭证是否办理", "资产已购买但未办理权属登记"),
            ("购房合同/购车合同/设备采购合同", "证明购买事实和资金来源", "有合同但权属登记与合同主体不符"),
            ("付款银行流水", "证明实际出资人", "付款账户与登记权利人不一致"),
            ("实际占有使用证据（物业费/水电费/经营场所照片）", "证明实际控制人", "被执行人实际占有使用但登记在他人名下"),
            ("关联方资产往来协议", "证明资产在关联方之间的流转", "资产在关联方之间转移但均未办理变更登记"),
        ],
        red_flag_threshold=[
            "被执行人实际出资购买但未办理权属登记",
            "资产登记在关联方或他人名下",
            "被执行人实际占有使用该财产",
        ],
        re_phase="涉案财产由被执行人实际出资购买并占有使用，虽未登记在被执行人名下，但依据实际出资和占有事实，应认定为被执行人的责任财产。",
        ro_phase="被执行人故意不办理权属登记或将登记在他人名下，意图规避执行，该行为不能改变被执行人实际控制该财产的事实。",
        rb_phase="登记权利人仅为名义持有人，不能以物权公示对抗申请执行人的强制执行请求权。",
        legal_route="TACTIC_CORP_FUND_HIDING",
        reinforcement_directions=[
            "调取全部购买合同和付款凭证（证明被执行人为实际出资人）",
            "收集被执行人实际占有使用该财产的证据（照片/视频/经营记录）",
            "申请律师调查令查询关联方的银行流水和资产情况",
        ],
    ),

    "C4": CorpTacticEvidenceSpec(
        tactic_code="C4",
        tactic_name="虚假诉讼保护（首封+以物抵债转移资产）",
        evidence_checklist=[
            ("虚假诉讼的判决/调解/仲裁文书", "证明存在关联诉讼", "调解结案/缺席判决/无实质对抗"),
            ("款项支付凭证（关联诉讼原告主张的债权）", "证明债权是否真实支付", "无真实款项支付或资金循环转账"),
            ("借款合同/借条/担保合同", "证明债权形成时间和基础法律关系", "债权形成时间在被执行人被申请执行之后"),
            ("查封/抵押登记时间线", "证明查封时间节点", "关联诉讼的查封/抵押早于/同步于申请执行人的保全"),
            ("以物抵债裁定及评估报告", "证明抵债价格是否合理", "以物抵债价格显著低于评估价"),
            ("关联案件双方工商/户籍信息", "证明原告与被告的关联关系", "原告与被告存在亲属/股权/人事关联"),
            ("被执行人及关联人银行流水", "证明资金是否真实流转", "资金到账后立即转回或提现"),
            ("关联案件庭审笔录", "证明是否有实质对抗", "双方无实质抗辩，疑似串通"),
        ],
        red_flag_threshold=[
            "关联诉讼以调解或缺席判决结案",
            "无真实款项支付，资金循环转账",
            "债权形成时间在被执行人被申请执行之后",
            "以物抵债价格显著低于评估价",
        ],
        re_phase="申请执行人依据生效法律文书对被执行人名下财产享有强制执行请求权，该权利优先于被执行人与关联人通过虚假诉讼制造的'债权'。",
        ro_phase="关联诉讼系被执行人与案外人恶意串通，以虚假诉讼方式转移资产，符合刑法第307条之一虚假诉讼罪构成要件；民事上依据民法典第538条，该转让行为应予撤销。",
        rb_phase="虚假诉讼中的'债权人'不享有真实债权，其对涉案财产的权利系虚构，不能排除申请执行人的强制执行。",
        legal_route="TACTIC_CORP_SHELL_TRANSFER",
        reinforcement_directions=[
            "向法院调取关联案件的庭审笔录（证明双方无实质对抗）",
            "申请审计机构对被执行人及关联人银行流水进行专项审计",
            "收集被执行人与'原告'之间的通讯记录/资金往来（证明恶意串通）",
            "向检察院申请启动虚假诉讼监督程序",
            "代理申请执行人提起第三人撤销之诉（民诉法第59条）",
        ],
    ),

    "C5": CorpTacticEvidenceSpec(
        tactic_code="C5",
        tactic_name="虚构债权债务关系设定抵押",
        evidence_checklist=[
            ("借款合同/贷款合同/担保合同", "证明主债务是否真实", "无真实转账记录或资金即进即出"),
            ("不动产/股权/设备抵押登记证明", "证明抵押登记时间", "抵押登记发生在执行期间或债务形成后"),
            ("抵押权人身份及与被执行人关系", "证明是否存在关联关系", "抵押权人为关联方或近亲属"),
            ("债务金额与抵押物价值对比", "证明是否合理", "债务金额与抵押物价值严重不匹配"),
            ("抵押权人银行放款流水", "证明是否真实放款", "无资金支付或资金绕一圈后回转"),
            ("被执行人银行流水（收款账户）", "证明资金最终去向", "资金到账后立即转至关联账户"),
            ("抵押权人营业执照/身份信息", "证明抵押权人是否有放款能力", "抵押权人为空壳公司或无经营记录"),
            ("抵押从未被实际主张的证据", "证明是否为'工具性抵押'", "抵押登记后从未有催收/诉讼/执行记录"),
        ],
        red_flag_threshold=[
            "主债务无真实转账记录",
            "抵押登记发生在执行期间或债务形成后",
            "抵押权人为关联方或空壳公司",
            "抵押从未被实际主张",
        ],
        re_phase="申请执行人依据生效法律文书对被执行人名下财产享有执行请求权，该权利不因被执行人其后设定虚假抵押权而受影响。",
        ro_phase="被执行人与抵押权人恶意串通，虚构债务并设定抵押权，属于民法典第538条'恶意延长其到期债权的履行期限'的行为，依法应予撤销。",
        rb_phase="虚构债务的抵押权不具有真实性，抵押权人不得以抵押权对抗申请执行人的执行请求权。",
        legal_route="TACTIC_CORP_SHELL_TRANSFER",
        reinforcement_directions=[
            "申请律师调查令查询抵押权人银行流水（证明无真实放款）",
            "调查抵押权人工商登记、股东信息、经营状态（证明为空壳公司）",
            "委托评估机构对抵押物进行价值评估（证明价值严重高估）",
            "向法院申请确认抵押合同无效之诉",
        ],
    ),

    "C6": CorpTacticEvidenceSpec(
        tactic_code="C6",
        tactic_name="虚构长期租赁关系（以租抵债阻止拍卖）",
        evidence_checklist=[
            ("租赁合同文本及签订日期", "证明租赁开始时间和租赁期限", "合同签订时间在查封之后，租期20年以上"),
            ("租金支付银行转账记录", "证明是否有真实租金支付", "无转账记录或一次性支付但无资金流"),
            ("物业费/水电费缴纳人信息", "证明实际占有使用人", "物业费/水电费由被执行人（出租人）缴纳"),
            ("被执行人与承租人关系证据", "证明是否存在关联关系", "承租人为关联方或近亲属"),
            ("承租人实际占有涉案资产的证据", "证明是否实际占有", "涉案资产由被执行人占有使用，承租人从未实际占有"),
            ("租金市场价格对比", "证明租金是否合理", "租金显著低于市场价"),
            ("租赁备案登记信息", "证明备案时间", "未备案或备案时间晚于查封"),
            ("承租人营业执照/经营地址", "证明是否有真实经营", "承租人注册地址与涉案资产地址不符"),
        ],
        red_flag_threshold=[
            "租赁合同签订时间在查封之后",
            "无真实租金支付记录",
            "涉案资产仍由被执行人实际占有使用",
            "承租人为关联方或近亲属",
        ],
        re_phase="依据民法典第725条，'买卖不破租赁'的适用前提是承租人在租赁物被查封前已合法占有涉案资产。申请执行人请求法院依法涤除该租赁权后进行拍卖。",
        ro_phase="经查，涉案资产的物业费、水电费均由被执行人缴纳，承租人从未实际占有使用，租赁关系系虚构。依据民法典第725条，'买卖不破租赁'的法定前提不成立，该租赁权不能阻却执行。",
        rb_phase="即便承租人主张租赁权，因其未能证明在查封前已合法占有涉案资产，不符合'买卖不破租赁'的法定构成要件，抗辩权不能成立。",
        legal_route="TACTIC_CORP_SHELL_TRANSFER",
        reinforcement_directions=[
            "向物业公司调取物业费缴纳记录（证明被执行人为实际缴费人）",
            "向电力公司/自来水公司/燃气公司调取户名及使用记录",
            "收集被执行人实际占有使用涉案资产的证据（照片/视频/经营记录）",
            "调查承租人是否有其他实际经营/居住地址证明",
        ],
    ),

    "C7": CorpTacticEvidenceSpec(
        tactic_code="C7",
        tactic_name="虚构买卖关系，案外人提执行异议阻挡执行",
        evidence_checklist=[
            ("案外人执行异议申请书", "证明异议类型和理由", "案外人主张所有权/租赁权/抵押权等"),
            ("基础法律关系证明（买卖合同/租赁合同/合作协议）", "证明基础法律关系是否真实", "存在C1/C2/C6所列虚假法律关系特征"),
            ("异议申请时间 vs 查封时间", "证明时间节点是否异常", "异议发生在执行程序启动后，疑似恶意阻却"),
            ("案外人与被执行人关系证据", "证明是否存在关联关系", "案外人与被执行人存在亲属/股权/人事关联"),
            ("案外人付款凭证", "证明是否支付合理对价", "无法提供银行转账记录或资金来源不明"),
            ("案外人实际占有涉案资产的证据", "证明是否满足占有要件", "无法提供充分实际占有证据"),
        ],
        red_flag_threshold=[
            "案外人与被执行人存在关联关系",
            "基础法律关系存在C1/C2/C6所列虚假特征",
            "案外人无法证明在查封前已合法占有",
            "异议时间节点异常（拍卖公告后立即提起）",
        ],
        re_phase="申请执行人依据生效法律文书对涉案财产享有执行请求权，该权利优先于案外人的实体权利主张。",
        ro_phase="案外人与被执行人恶意串通，虚构买卖/租赁等法律关系，意图阻却执行程序。依据民法典第725条，'买卖不破租赁'须以查封前已合法占有为前提；依据民法典第235条，所有权返还请求权须证明合法取得。",
        rb_phase="案外人援引所有权或租赁权排除执行，但其不能证明：①支付了合理对价；②在查封前已合法占有涉案财产。上述抗辩权均不能成立。",
        legal_route="TACTIC_CORP_SHELL_TRANSFER",
        reinforcement_directions=[
            "对案外人的基础法律关系进行专项审查（套用C1/C2/C6审查标准）",
            "收集案外人与被执行人恶意串通的证据（通讯记录/资金往来）",
            "申请法院对案外人实际占有情况进行现场调查",
            "准备质证意见，对案外人的证据逐项驳斥",
        ],
    ),

    "C8": CorpTacticEvidenceSpec(
        tactic_code="C8",
        tactic_name="脱壳（金蝉脱壳——核心业务/人员/客户转移至新公司，原公司空壳化）",
        evidence_checklist=[
            ("原公司工商登记信息（含历史）", "证明公司变更历史和资产流向", "原公司资产转移至新公司但无合理对价"),
            ("新公司工商登记信息", "证明新公司与原公司的关联", "股东/高管/注册地址与原公司高度重合"),
            ("核心业务合同/项目文件", "证明业务是否发生了实质性转移", "核心业务合同转至新公司名下"),
            ("员工社保/工资发放记录（原公司）", "证明人员是否随业务转移", "原公司员工大量离职并转入新公司"),
            ("原公司银行流水", "证明资产转移路径", "大额资金转入新公司账户后随即转出"),
            ("客户/供应商往来凭证", "证明客户资源是否被转移", "原公司客户转至新公司，原公司无营业收入"),
            ("原公司纳税申报记录", "证明原公司是否空壳化", "原公司纳税申报为零或极低，新公司正常纳税"),
            ("原公司被执行案件汇总", "证明原公司是否已被多个债权人起诉", "原公司大量诉讼/执行案件，新公司正常经营"),
        ],
        red_flag_threshold=[
            "原公司与新公司股东/高管/注册地址高度重合",
            "核心业务/人员/客户转移至新公司",
            "原公司资产大幅减少但无合理对价",
            "原公司大量诉讼/执行案件，新公司正常经营",
        ],
        re_phase="申请执行人对原公司（被执行人）的债权经生效法律文书确认，原公司通过脱壳方式将资产转移至新公司，规避申请执行人的执行请求权。",
        ro_phase="原公司与新公司在人员、业务、财务上高度混同，新公司系原公司的延续，依据新《公司法》第23条之过度支配与控制条款，原公司债务应由新公司承担连带责任。",
        rb_phase="新公司以'独立法人'地位抗辩，但人员混同+业务混同+财务混同三重事实已构成人格混同，独立法人人格应被否认。",
        legal_route="TACTIC_CORP_SHELL_SWAP",
        reinforcement_directions=[
            "委托律师调查原公司与新公司的工商档案（股东/董监高/注册地址对比）",
            "收集原公司与新公司人员高度重合的证据（社保记录/工资流水）",
            "调取原公司银行流水（证明资产转移路径）",
            "收集原公司客户/供应商转向新公司的证据（合同/往来凭证）",
            "追加新公司为被执行人（横向人格否认，新《公司法》第23条）",
        ],
    ),

    "C9": CorpTacticEvidenceSpec(
        tactic_code="C9",
        tactic_name="公司资金放在他人名下（会计/股东/股东配偶/员工账户）",
        evidence_checklist=[
            ("公司银行账户流水（全部账户）", "证明公司资金流向", "大额资金转入个人账户后无法说明用途"),
            ("公司财务凭证/记账凭证", "证明资金流转的会计处理", "资金转入个人账户但无对应财务凭证"),
            ("实际收款个人账户的银行流水", "证明资金最终去向", "资金到账后立即转至第三方或提现"),
            ("收款个人与公司/股东的关系证据", "证明是否存在关联关系", "收款人为会计/股东/配偶/员工"),
            ("公司会计报表/审计报告", "证明公司财务是否规范", "体外循环资金未在报表中反映"),
            ("个人所得税/社保缴纳记录", "证明收款人是否为公司在职员工", "收款人社保由公司缴纳但账户为公司账户之外"),
            ("公司大额支出审批记录", "证明资金支出是否经过公司正常审批", "资金支出无内部审批记录或审批异常"),
        ],
        red_flag_threshold=[
            "公司大额资金转入个人账户",
            "收款个人与公司/股东有密切关系",
            "资金到账后无法说明用途或立即转出",
            "公司财务报表未反映该笔资金往来",
        ],
        re_phase="公司账户资金属于公司法人独立财产，被执行人将公司资金转移至个人账户，削弱了公司的偿还能力，损害了债权人利益。",
        ro_phase="被执行人作为公司控股股东/实际控制人，将公司资金转移至关联个人账户，构成股东与公司财产混同，依据新《公司法》第23条，应对公司债务承担连带责任。",
        rb_phase="收款个人主张该资金为'工资''备用金''借款'等，但未能提供相应税务凭证/借款合同等佐证，不能成立。",
        legal_route="TACTIC_CORP_FUND_HIDING",
        reinforcement_directions=[
            "申请律师调查令查询公司全部银行账户流水",
            "向税务局查询公司及关联个人的税务申报情况",
            "委托会计师事务所对被执行人公司进行专项审计",
            "收集公司与个人账户资金混同的证据（用于人格否认诉讼）",
        ],
    ),

    "C10": CorpTacticEvidenceSpec(
        tactic_code="C10",
        tactic_name="更改公司名称、更换注册地址、跨区域转移工商登记",
        evidence_checklist=[
            ("公司工商登记信息（含历史变更记录）", "证明名称/地址变更时间线", "变更发生在诉讼/执行期间"),
            ("公司不动产物权登记信息", "证明核心资产是否留在原公司", "核心资产未随公司变更而变更"),
            ("公司银行账户信息（开户行/账号）", "证明银行账户是否保持不变", "银行账户未随注册地变更而迁移"),
            ("公司在新注册地的经营证据（租赁合同/房产证明）", "证明是否真实在新地址经营", "注册地址变更但无实际经营迹象"),
            ("公司税务登记信息", "证明税务关系是否同步变更", "税务登记仍保留在原注册地"),
            ("申请执行人与被执行人的案件时间线", "证明变更时间与诉讼时间的关系", "变更发生在诉讼/执行期间，疑似刻意规避"),
        ],
        red_flag_threshold=[
            "公司名称/注册地址变更发生在诉讼/执行期间",
            "核心资产未随公司变更而变更",
            "新注册地址无实际经营迹象",
            "变更后公司仍由原股东/实际控制人控制",
        ],
        re_phase="公司名称和注册地址的变更不影响公司法人资格的连续性，被执行人仍为该公司，申请执行人对其享有的债权不受公司名称/地址变更影响。",
        ro_phase="被执行人通过变更名称/地址增加债权人查找财产的难度，但核心资产仍登记在被执行人名下，变更行为不能阻却执行。",
        rb_phase="被执行人主张'公司已迁址，原公司不存在'的抗辩不能成立——公司法人资格连续，变更前的债务仍由变更后的公司承担。",
        legal_route="TACTIC_CORP_NAME_ADDR_CHANGE",
        reinforcement_directions=[
            "向工商登记机关调取公司完整的历史变更记录",
            "调查公司在新注册地址的实际经营情况（现场走访/物业核实）",
            "排查被执行人名下核心资产的查封/抵押状态",
            "确认被执行人的银行账户、不动产、股权等财产线索（猎犬座穿透）",
        ],
    ),

    "C11": CorpTacticEvidenceSpec(
        tactic_code="C11",
        tactic_name="更换法定代表人、撤换股东及董监高",
        evidence_checklist=[
            ("公司工商登记信息（含历史）", "证明法定代表人/股东/董监高变更时间线", "变更发生在诉讼/执行期间"),
            ("法定代表人变更文件（股东会决议/任命书）", "证明变更是否经过真实决议", "变更文件无实际股东签名或签章异常"),
            ("新老法定代表人身份信息", "证明新老法定代表人的关系", "新法定代表人为老方法定代表人的亲属/员工/关联方"),
            ("股权转让协议（涉及股东变更）", "证明股权转让时间、价格、对手方", "股权转让发生在诉讼/执行期间且无合理对价"),
            ("被执行人在变更前后的涉诉案件统计", "证明变更是否伴随大量诉讼", "变更前大量诉讼涌入，变更后新公司正常经营"),
            ("新任法定代表人的背景调查", "证明其是否有实际经营能力", "新法定代表人为无资产/无收入的自然人"),
        ],
        red_flag_threshold=[
            "法定代表人/股东变更发生在诉讼/执行期间",
            "新法定代表人/股东与原实际控制人有密切关系",
            "股权转让无合理对价或无偿",
            "变更后公司由原实际控制人实际控制",
        ],
        re_phase="公司法定代表人和股东的变更不影响公司债务的承担，被执行人仍为该公司，原法定代表人和原股东在特定条件下仍可被追加为被执行人。",
        ro_phase="被执行人通过变更法定代表人和股东逃避执行，但实际控制人未变更（新法定代表人为傀儡）。依据新《公司法》第23条，应追究实际控制人的连带责任。",
        rb_phase="即便法定代表人/股东发生变更，在以下情况下仍可被追加：(1)原股东未履行出资义务→追加规定第17条；(2)财产混同→人格否认→追加规定第20条。",
        legal_route="TACTIC_CORP_NAME_ADDR_CHANGE",
        reinforcement_directions=[
            "向工商登记机关调取公司完整的历史变更记录（法定代表人/股东）",
            "调查新法定代表人与原实际控制人的社会关系（户籍/社保/商业往来）",
            "收集被执行人在变更后仍由原实际控制人实际运营的证据",
            "评估是否满足追加原股东/原法定代表人为被执行人的条件",
        ],
    ),

    "C12": CorpTacticEvidenceSpec(
        tactic_code="C12",
        tactic_name="克隆（冒名登记——设立与被执行人同名或近似公司混淆执行）",
        evidence_checklist=[
            ("被执行人名下全部公司工商登记信息", "证明是否存在字号近似的关联公司", "存在与被执行人字号高度近似的另一家公司"),
            ("两家公司股东/法定代表人工商登记对比", "证明实际控制人是否同一", "两家公司实际控制人为同一人或高度重合"),
            ("两家公司经营范围/注册地址/联系方式对比", "证明是否为刻意混淆", "经营范围、地址、联系方式高度重合或完全一致"),
            ("涉案法律文书/执行案件信息", "证明申请执行人是否曾混淆被执行主体", "申请执行人曾误将克隆公司当作被执行人起诉/申请执行"),
            ("两家公司银行账户信息对比", "证明是否存在财务混同", "两家公司账户之间有频繁资金往来"),
            ("两家公司实际经营地现场走访", "证明是否为同一经营主体", "两家公司实际在同一地址经营，门牌/标识相同"),
        ],
        red_flag_threshold=[
            "两家公司字号高度近似，实际控制人同一",
            "经营范围/地址/联系方式高度重合",
            "申请执行人曾误认被执行主体",
            "两家公司存在财务混同迹象",
        ],
        re_phase="克隆公司系被执行人刻意设立的与原公司近似的主体，意图混淆申请执行人，规避执行。两家公司实质为同一经营主体，应合并执行。",
        ro_phase="被执行人通过克隆公司进行经营活动，但实质为一个经营主体、一个人格。依据新《公司法》第23条之规定，克隆公司与原公司应承担连带责任。",
        rb_phase="克隆公司主张'独立法人、独立经营'的抗辩不能成立——字号近似+实际控制人同一+经营混同三重事实已构成人格混同。",
        legal_route="TACTIC_CORP_CLONING",
        reinforcement_directions=[
            "委托律师调查两家公司工商档案（全面比对股东/高管/注册地址）",
            "收集两家公司经营地同一的证据（现场走访/照片/视频）",
            "调取两家公司银行账户流水（证明财务混同）",
            "追加克隆公司为被执行人（横向人格否认）",
        ],
    ),

    "C13": CorpTacticEvidenceSpec(
        tactic_code="C13",
        tactic_name="违法减资（未依法通知已知债权人，以减资为名抽逃资产）",
        evidence_checklist=[
            ("公司股东会减资决议", "证明减资时间和减资幅度", "减资发生在诉讼/执行期间"),
            ("公司工商变更登记信息（注册资本变更）", "证明减资是否完成工商变更", "已完成减资变更登记"),
            ("公司在减资前后的银行流水", "证明减资资金去向", "减资款项退回股东账户后无法说明用途"),
            ("减资公告及债权人通知记录", "证明是否依法通知已知债权人", "仅在报纸上公告，未逐一通知已知债权人"),
            ("申请执行人作为已知债权人的证据", "证明申请执行人在减资时已是债权人", "减资时申请执行人已有生效判决或债务已到期"),
            ("公司债权人名单及债务明细", "证明已知债权人的范围", "减资时已知债权人数量与实际债务规模严重不符"),
            ("公司减资前后的财务报表", "证明减资前后公司偿债能力变化", "减资后公司偿债能力大幅下降但资产未用于清偿债务"),
        ],
        red_flag_threshold=[
            "减资发生在诉讼/执行期间",
            "仅公告未逐一通知已知债权人",
            "减资款项退回股东账户后无法说明用途",
            "减资后公司偿债能力大幅下降",
        ],
        re_phase="申请执行人作为被执行人的已知债权人，在公司减资时依法享有要求公司清偿债务或提供担保的权利。公司违法减资削弱了被执行人的偿还能力。",
        ro_phase="依据新《公司法》第226条，违法减资的股东应在减资范围内对公司债务承担补充赔偿责任。公司通过减资将资产返还股东，构成抽逃出资。",
        rb_phase="公司主张'减资已公告，债权人未申报'的抗辩不能成立——申请执行人在减资时已是已知债权人，公司未逐一通知即构成违法。",
        legal_route="TACTIC_CORP_ILLEGAL_REDUCTION",
        reinforcement_directions=[
            "向工商登记机关调取公司减资的完整工商档案",
            "向法院调取申请执行人与被执行人案件的立案/判决时间（证明减资时申请执行人已是债权人）",
            "收集减资款项退回股东账户的银行流水证据",
            "代理申请执行人起诉，要求股东在减资范围内承担补充赔偿责任",
        ],
    ),

    "C14": CorpTacticEvidenceSpec(
        tactic_code="C14",
        tactic_name="违法清算（未经依法清算即办理注销，或以虚假清算报告骗取注销）",
        evidence_checklist=[
            ("公司注销登记信息", "证明公司注销时间和注销方式", "公司在诉讼/执行期间注销"),
            ("清算报告/清算组成立文件", "证明清算是否真实进行", "清算报告与实际资产状况严重不符"),
            ("公司注销前的资产负债表/财务报表", "证明清算时的真实资产状况", "清算报告显示资产为零或极低，但实际存在大量资产"),
            ("公司银行账户流水（注销前）", "证明清算资产去向", "公司资产在清算期间被转移或分配给股东"),
            ("公司债务清偿记录", "证明是否对已知债权人进行了清偿", "清算报告显示债务已清偿，但申请执行人未获清偿"),
            ("清算组成员身份信息", "证明清算组成员是否适格", "清算组成员为股东近亲属或公司员工，与债权人存在利益冲突"),
            ("税务注销/社保注销记录", "证明注销程序是否完整", "税务注销在债权申报期限届满前完成"),
            ("公司不动产物权/股权/应收账款清单", "证明清算时是否遗漏了主要资产", "公司注销后仍存在可执行的财产线索"),
        ],
        red_flag_threshold=[
            "公司在诉讼/执行期间注销",
            "清算报告显示资产为零或极低，但实际存在资产",
            "申请执行人未获清算清偿",
            "清算组成员不适格或存在利益冲突",
        ],
        re_phase="公司未经依法清算即办理注销登记，损害了债权人利益。依据《公司法》司法解释二第20条，公司注销后债权人可向股东主张赔偿责任。",
        ro_phase="公司以虚假清算报告骗取注销，清算组成员应对公司债务承担连带赔偿责任。申请执行人可将清算组成员追加为被执行人。",
        rb_phase="股东主张'公司已合法注销'的抗辩不能成立——违法清算不影响股东对公司债务的连带责任。",
        legal_route="TACTIC_CORP_ILLEGAL_LIQUIDATION",
        reinforcement_directions=[
            "向工商登记机关调取公司注销的完整档案（含清算报告）",
            "委托审计机构对公司注销前的财务状况进行专项审计",
            "收集公司在清算期间转移资产的证据（银行流水穿透）",
            "追加清算组成员为被执行人（公司法解释二第20条）",
            "代理申请执行人提起清算责任纠纷诉讼",
        ],
    ),

    "C15": CorpTacticEvidenceSpec(
        tactic_code="C15",
        tactic_name="强制吊销（公司因违法经营被吊销营业执照但未清算）",
        evidence_checklist=[
            ("公司吊销营业执照行政处罚决定书", "证明吊销时间、吊销原因", "公司在诉讼/执行期间被吊销"),
            ("公司吊销后的工商登记状态", "证明公司是否已注销", "公司被吊销后未办理注销登记，仍具有法人资格"),
            ("公司吊销后的资产状况", "证明主要财产是否仍在公司名下", "公司被吊销后资产未被妥善处置"),
            ("公司吊销后是否继续经营", "证明是否存在违法经营持续", "公司被吊销后仍在实际控制人的操控下继续经营"),
            ("公司股东/实际控制人的其他公司情况", "证明是否存在脱壳行为", "公司被吊销后，原股东/实际控制人另设新公司继续经营同类业务"),
            ("申请执行人的债权在吊销时是否已到期", "证明申请执行人是否为已知债权人", "吊销时申请执行人的债权已到期但未获清偿"),
        ],
        red_flag_threshold=[
            "公司在诉讼/执行期间被吊销营业执照",
            "公司被吊销后未依法进行清算",
            "公司主要资产仍在公司名下但处于无人管理状态",
            "原股东/实际控制人另设新公司继续经营",
        ],
        re_phase="公司被吊销营业执照后，应在15日内成立清算组进行清算（公司法第183条）。公司逾期不成立清算组清算的，债权人可申请人民法院指定有关人员组成清算组清算。",
        ro_phase="公司被吊销后未依法清算，股东/实际控制人应继续承担清算义务。依据公司法解释二第18条，股东/实际控制人应对公司债务承担连带赔偿责任。",
        rb_phase="股东主张'公司已吊销，债务已消灭'的抗辩不能成立——吊销不等于注销，公司法人资格在注销前仍然存续，债务不因吊销而消灭。",
        legal_route="TACTIC_CORP_ILLEGAL_LIQUIDATION",
        reinforcement_directions=[
            "向工商登记机关查询公司吊销后的工商状态",
            "调查公司被吊销后的资产状况和实际控制人情况",
            "收集股东/实际控制人另设新公司继续经营的证据",
            "代理申请执行人向法院申请对被吊销公司进行强制清算",
            "追加股东/实际控制人为被执行人（公司法解释二第18条）",
        ],
    ),

    "C16": CorpTacticEvidenceSpec(
        tactic_code="C16",
        tactic_name="违法破产（通过破产程序逃废债务，或在破产程序中个别清偿）",
        evidence_checklist=[
            ("破产案件受理裁定书", "证明破产程序启动时间", "破产申请发生在诉讼/执行期间或债务即将到期时"),
            ("债权人申报债权资料", "证明申请执行人是否及时申报债权", "申请执行人未获通知或错过债权申报期限"),
            ("破产债权表/债权确认裁定", "证明申请执行人的债权是否被确认", "申请执行人的债权被以各种理由削减或不予确认"),
            ("破产财产分配方案", "证明破产财产是否被个别清偿", "部分债权人在破产前获得个别清偿"),
            ("破产前一年内债务人财产变动情况", "证明是否存在个别清偿/偏颇清偿", "破产前一年内对个别债权人进行了清偿（破产法第32条）"),
            ("债务人银行流水（破产申请前）", "证明是否存在转移资产行为", "破产前有大额资产转移至关联方"),
            ("关联企业的合并破产/实质合并审理裁定", "证明是否存在关联企业实质合并破产逃债", "多家关联公司同时进入破产程序，实质合并审理"),
            ("破产管理人履职报告", "证明破产管理是否尽职", "破产管理人未追收债务人应收账款或未尽职调查隐性资产"),
        ],
        red_flag_threshold=[
            "破产申请发生在诉讼/执行期间",
            "申请执行人的债权被削减或不予确认",
            "破产前一年内存在个别清偿/偏颇清偿行为",
            "关联企业同时破产，疑似通过实质合并逃债",
        ],
        re_phase="申请执行人作为债权人，有权参加破产程序并就破产财产获得公平清偿。破产程序不应成为债务人逃废债务的工具。",
        ro_phase="依据破产法第32条，破产申请受理前一年内的个别清偿行为，管理人有权请求撤销。依据破产法第40条，债务人在破产申请前恶意减少财产的行为，管理人有权追回。",
        rb_phase="破产程序中个别债权人的'优先受偿'主张（如有担保债权）不能对抗申请执行人对债务人整体财产的合法权益。",
        legal_route="TACTIC_CORP_SHELL_TRANSFER",
        reinforcement_directions=[
            "向破产法院调取破产案件的完整卷宗材料",
            "审查破产债权表，确认申请执行人的债权是否被错误削减",
            "委托审计机构对破产前一年内的银行流水进行穿透审计",
            "向管理人提出破产撤销权/追回权申请（破产法第32条/第40条）",
            "如关联企业实质合并破产，代理申请执行人提出异议（主张分别清偿）",
            "向法院/检察院举报破产程序中的违法行为",
        ],
    ),

    "C17": CorpTacticEvidenceSpec(
        tactic_code="C17",
        tactic_name="其他逃废债行为（上述16类以外的其他规避执行行为）",
        evidence_checklist=[
            ("被执行人名下全部银行账户信息", "证明是否将存款转移至其他账户", "有大量资金流入但余额异常偏低"),
            ("被执行人名下不动产/车辆/股权/知识产权登记信息", "证明是否将财产分散登记", "财产分散登记在多个关联方或他人名下"),
            ("被执行人主要结算账户的收支明细", "证明是否存在大量关联交易", "与特定关联方的交易金额异常且无商业合理理由"),
            ("被执行人日常经营的收支渠道", "证明是否通过体外循环隐匿收入", "营业收入通过私人账户或第三方平台收取，未入公账"),
            ("被执行人实际控制的其他企业情况", "证明是否存在通过关联交易转移利润", "被执行人控制的关联方以异常高价从被执行人采购或低价供货"),
            ("被执行人在诉讼/执行期间的大额支出记录", "证明是否存在恶意消耗资产行为", "诉讼/执行期间有大额'捐赠''赞助''咨询费'等异常支出"),
        ],
        red_flag_threshold=[
            "被执行人银行账户余额异常偏低，但有大量交易流水",
            "财产分散登记在多个关联方或他人名下",
            "营业收入通过体外循环，未入公账",
            "诉讼/执行期间有大额异常支出",
        ],
        re_phase="申请执行人依据生效法律文书对被执行人享有债权，被执行人的一切财产变动行为均不得损害申请执行人的合法权益。",
        ro_phase="被执行人通过体外循环、关联交易、异常支出等方式隐匿、转移财产，规避执行。申请执行人有权请求法院对被执行人采取限制高消费、限制出境、罚款、拘留等强制措施。",
        rb_phase="被执行人主张'资金用于正常经营/还款'的抗辩，须提供相应证据证明。不能证明合理用途的隐匿转移行为，应认定为规避执行。",
        legal_route="TACTIC_CORP_FUND_HIDING",
        reinforcement_directions=[
            "申请律师调查令查询被执行人全部银行账户流水",
            "委托审计机构对被执行人进行专项财务审计",
            "收集被执行人通过关联交易转移利润的证据",
            "申请法院对被执行人采取限制高消费/限制出境措施",
            "情节严重的，依法追究被执行人拒执罪刑事责任（刑法第313条）",
        ],
    ),
}


# ───────────────────────────────────────────────────────────────
#  审查报告数据模型
# ───────────────────────────────────────────────────────────────

@dataclass
class CorpTacticAuditResult:
    tactic_code: str
    tactic_name: str
    status: str              # CONFIRMED / SUSPECTED / RULED_OUT / UNCHECKED
    evidence_strength: str   # HIGH / MEDIUM / LOW
    triggered_red_flags: list
    key_evidence_obtained: list
    evidence_gaps: list
    countermeasure_plan: str
    three_stage_rebuttal: dict
    confidence: float


@dataclass
class CorpAuditReport:
    case_id: str
    debtor_name: str
    debtor_type: str = "legal_entity"
    audit_date: str = ""
    overall_assessment: str = ""
    identified_tactics: list = field(default_factory=list)
    priority_targets: list = field(default_factory=list)
    next_steps: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ───────────────────────────────────────────────────────────────
#  核心审查引擎
# ───────────────────────────────────────────────────────────────

class LegalEntityAuditor:
    """
    营利法人逃废债伎俩证据审查引擎
    用法：
      auditor = LegalEntityAuditor(case_id="XXX", debtor_name="某公司")
      report = auditor.run_audit(evidence_inputs)
    """

    TACTIC_CODES = list(TACTIC_SPECS.keys())

    def __init__(self, case_id: str, debtor_name: str):
        self.case_id = case_id
        self.debtor_name = debtor_name
        self.audit_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    def audit_tactic(self, tactic_code: str,
                     evidence_status: Optional[dict] = None) -> CorpTacticAuditResult:
        spec = TACTIC_SPECS.get(tactic_code)
        if not spec:
            raise ValueError(f"Unknown tactic_code: {tactic_code}")

        es = evidence_status or {}

        # 红灯信号触发
        hit_count = sum(1 for ev_name in es if es.get(ev_name, False))

        # 证据已获取/缺失分类
        obtained = []
        gaps = []
        for ev_name, ev_use, _ in spec.evidence_checklist:
            if es.get(ev_name, False):
                obtained.append(f"{ev_name}（用途：{ev_use}）")
            else:
                gaps.append(f"{ev_name}（用途：{ev_use}）")

        obtained_count = sum(1 for v in es.values() if v)
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

        return CorpTacticAuditResult(
            tactic_code=tactic_code,
            tactic_name=spec.tactic_name,
            status=status,
            evidence_strength=strength,
            triggered_red_flags=spec.red_flag_threshold[:],
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

    def run_audit(self, evidence_inputs: Optional[dict] = None,
                  confirmed_only: bool = False) -> CorpAuditReport:
        """
        运行全量审查。

        evidence_inputs 格式：
          {
            "C1": {"证据名": True/False, ...},
            ...
          }
        """
        results = []
        for code in self.TACTIC_CODES:
            es = evidence_inputs.get(code, {}) if evidence_inputs else {}
            result = self.audit_tactic(code, es)
            if confirmed_only and result.status in ("RULED_OUT", "UNCHECKED"):
                continue
            results.append(result)

        results.sort(key=lambda x: x.confidence, reverse=True)

        priority = [r.tactic_code for r in results
                    if r.status == "CONFIRMED" and r.evidence_strength == "HIGH"]

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

        next_steps = []
        for r in results:
            if r.status in ("CONFIRMED", "SUSPECTED") and r.evidence_gaps:
                next_steps.append(
                    f"{r.tactic_code} {r.tactic_name}：补充证据 {r.evidence_gaps[0].split('（')[0]}"
                )

        return CorpAuditReport(
            case_id=self.case_id,
            debtor_name=self.debtor_name,
            debtor_type="legal_entity",
            audit_date=self.audit_date,
            overall_assessment=overall,
            identified_tactics=[asdict(r) for r in results],
            priority_targets=priority,
            next_steps=next_steps[:10],
        )

    def print_report(self, report: CorpAuditReport):
        print(f"\n{'='*60}")
        print(f"  营利法人逃废债伎俩识别与反制报告")
        print(f"{'='*60}")
        print(f"  案件编号：{report.case_id}")
        print(f"  被执行人：{report.debtor_name}（法人）")
        print(f"  审核日期：{report.audit_date}")
        print(f"{'─'*60}")
        print(f"  【总体评估】{report.overall_assessment}")
        print(f"{'─'*60}")

        for t in report.identified_tactics:
            icons = {"CONFIRMED": "🔴", "SUSPECTED": "🟡",
                     "RULED_OUT": "⚪", "UNCHECKED": "⬜"}
            print(f"\n  {icons.get(t['status'], '⚪')} [{t['tactic_code']}] {t['tactic_name']}")
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

def main():
    parser = argparse.ArgumentParser(description="营利法人逃废债伎俩证据审查引擎")
    parser.add_argument("--case-id", default="UNKNOWN")
    parser.add_argument("--debtor-name", default="未知公司")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--json-output", action="store_true")
    parser.add_argument("--confirmed-only", action="store_true")

    args = parser.parse_args()

    evidence_inputs = {}
    if args.interactive:
        for code in TACTIC_SPECS.keys():
            spec = TACTIC_SPECS[code]
            print(f"\n【{code}】{spec.tactic_name}")
            evidence_inputs[code] = {}
            for ev_name, ev_use, _ in spec.evidence_checklist:
                ans = input(f"  {ev_name}（{ev_use}）[y/n]: ").strip().lower()
                evidence_inputs[code][ev_name] = ans in ("y", "yes")

    auditor = LegalEntityAuditor(args.case_id, args.debtor_name)
    report = auditor.run_audit(evidence_inputs if args.interactive else None,
                                confirmed_only=args.confirmed_only)

    if args.json_output:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        auditor.print_report(report)


if __name__ == "__main__":
    main()
