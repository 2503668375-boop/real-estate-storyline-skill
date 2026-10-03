#!/usr/bin/env python3
"""审查8.3外部成品，强制前策正向因果、论断边界与完整提案责任。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

根 = Path(__file__).resolve().parents[1]
规则 = json.loads((根 / "references" / "统一规则.json").read_text(encoding="utf-8"))


def 纯化(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


class 提案解析器(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.页面 = []
        self.当前 = None
        self.深度 = 0
        self.忽略 = 0
        self.标题深度 = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        if self.当前 is None and 规则["HTML页面类"] in classes:
            self.当前 = {
                "section": (a.get(规则["HTML外部章节属性"]) or "").strip(),
                "prototype": (a.get("data-prototype") or "").strip(),
                "proof": (a.get(规则.get("HTML主线属性", "data-proof-node")) or "").strip(),
                "visual_role": (a.get(规则.get("HTML视觉角色属性", "data-visual-role")) or "").strip(),
                "evidence": (a.get("data-evidence-id") or "").strip(),
                "decision": (a.get("data-decision") or "").strip(),
                "action": (a.get("data-action") or "").strip(),
                "kind": (a.get("data-page-kind") or "").strip(),
                "source": (a.get("data-source-id") or "").strip(),
                "metric": (a.get("data-metric") or "").strip(),
                "owner": (a.get("data-owner") or "").strip(),
                "deadline": (a.get("data-deadline") or "").strip(),
                "artifact": (a.get("data-artifact") or "").strip(),
                "quote": (a.get("data-quote") or "").strip(),
                "period": (a.get("data-period") or "").strip(),
                "comparison": (a.get("data-comparison-id") or "").strip(),
                "chart": (a.get("data-chart-id") or a.get("data-table-id") or "").strip(),
                "impact": (a.get("data-impact") or "").strip(),
                "text": [],
                "title": [],
                "cards": 0,
            }
            self.深度 = 1
        elif self.当前 is not None and tag not in self.VOID:
            self.深度 += 1
        if self.当前 is not None and any("card" in c.lower() or "tile" in c.lower() for c in classes):
            self.当前["cards"] += 1
        if self.当前 is not None and tag in {"h1", "h2", "h3"}:
            self.标题深度 += 1
        if tag in {"script", "style"}:
            self.忽略 += 1

    def handle_startendtag(self, tag, attrs):
        return

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.忽略:
            self.忽略 -= 1
        if self.当前 is not None:
            if tag in {"h1", "h2", "h3"} and self.标题深度:
                self.标题深度 -= 1
            self.深度 -= 1
            if self.深度 == 0:
                self.页面.append(self.当前)
                self.当前 = None

    def handle_data(self, data):
        if self.当前 is not None and not self.忽略:
            self.当前["text"].append(data)
            if self.标题深度:
                self.当前["title"].append(data)


def 首次位置(页面, section):
    for i, p in enumerate(页面):
        if p["section"] == section:
            return i
    return None


def 词覆盖(text, words):
    return [w for w in words if 纯化(w).lower() in text.lower()]


def 审查(path: Optional[Path], 类型: str, raw: Optional[str] = None):
    if raw is None:
        try:
            raw = path.read_text(encoding="utf-8", errors="strict")
        except Exception as e:
            return [f"无法读取UTF-8 HTML：{e}"], []

    parser = 提案解析器()
    parser.feed(raw)
    pages = parser.页面
    失败, 提醒 = [], []
    n = len(pages)

    if not n:
        return ["没有识别到class=slide的页面"], []

    lo, hi = 规则["交付页数"][类型]
    if n < lo:
        提醒.append(f"{类型}提案为{n}页，低于常规规模{lo}页；只要每页信息完整，可作为精简决策提案交付，禁止为了凑页补内容")
    if n > hi:
        失败.append(f"{类型}提案共{n}页，超过{hi}页；先合并重复内容")

    visible = [纯化("".join(p["text"])) for p in pages]
    full = "".join(visible)

    空泛填页语 = [
        "关键事实", "本页推导", "本章推导", "管理、风险与结语",
        "管理风险与结语", "贵不是问题", "贵而不可证明才是问题",
        "让真实成交决定下一步",
    ]
    命中空泛填页语 = [w for w in 空泛填页语 if 纯化(w) in full]
    if 命中空泛填页语:
        失败.append("外部主稿出现无项目数据、参数或动作的填页话术：" + "、".join(命中空泛填页语))

    无信息标记页 = []
    for i, p in enumerate(pages):
        if p["section"] == "appendix":
            continue
        标记 = [p["evidence"], p["decision"], p["action"]]
        if not any(len(x) >= 1 for x in 标记):
            无信息标记页.append(i + 1)
    if 无信息标记页:
        失败.append(
            "以下外部页缺少不显示的信息责任标记（data-evidence-id、data-decision、data-action 至少一项），"
            "无法证明其提供了新增事实、参数、方案或行动：" + "、".join(map(str, 无信息标记页))
        )

    免登记原型 = {"cover", "chapter", "section", "end", "contents"}
    缺页面类型 = []
    缺来源 = []
    类型责任不足 = []
    标题空泛 = []
    for i, p in enumerate(pages, 1):
        if p["section"] == "appendix" or p["prototype"] in 免登记原型:
            continue
        if p["kind"] not in 规则.get("外部页面类型", []):
            缺页面类型.append(i)
            continue
        if len(p["source"]) < 6:
            缺来源.append(i)
        if p["kind"] == "evidence":
            合格 = (
                len(p["evidence"]) >= 3 and len(p["metric"]) >= 8
                and len(p["period"]) >= 6 and len(p["comparison"]) >= 5
                and len(p["chart"]) >= 4 and len(p["impact"]) >= 8
                and len(纯化("".join(p["text"]))) >= 80
            )
        elif p["kind"] == "decision":
            合格 = len(p["decision"]) >= 10 and len(p["owner"]) >= 2 and len(p["deadline"]) >= 8
        elif p["kind"] == "product-proof":
            合格 = len(p["evidence"]) >= 3 and len(p["artifact"]) >= 5
        elif p["kind"] == "customer-voice":
            合格 = len(p["quote"]) >= 12 and len(p["evidence"]) >= 3
        elif p["kind"] == "operation":
            合格 = len(p["action"]) >= 10 and len(p["owner"]) >= 2 and len(p["deadline"]) >= 8 and len(p["artifact"]) >= 5
        elif p["kind"] == "concept":
            合格 = len(p["evidence"]) >= 3 and (len(p["artifact"]) >= 5 or len(p["metric"]) >= 8)
        else:
            合格 = True
        if not 合格:
            类型责任不足.append(i)
        标题 = 纯化("".join(p["title"]))
        if any(纯化(w) in 标题 for w in 规则.get("外部标题空洞框架词", [])):
            标题空泛.append(i)
    if 缺页面类型:
        失败.append("以下外部页没有声明有效页面类型，不能以通用卡片充数：" + "、".join(map(str, 缺页面类型)))
    if 缺来源:
        失败.append("以下外部页未登记可回溯来源，无法判断内容是否来自项目事实：" + "、".join(map(str, 缺来源)))
    if 类型责任不足:
        失败.append("以下外部页缺少该类型的证据、对象、责任人、日期或交付物，属于空泛框架页：" + "、".join(map(str, 类型责任不足)))
    if 标题空泛:
        失败.append("以下外部页标题以抽象框架代替项目对象和证据，应重写或删除：" + "、".join(map(str, 标题空泛)))

    重复页 = []
    已见正文 = {}
    for i, (p, t) in enumerate(zip(pages, visible), 1):
        if p["section"] == "appendix" or len(t) < 30:
            continue
        if t in 已见正文:
            重复页.append(f"{已见正文[t]}与{i}")
        else:
            已见正文[t] = i
    if 重复页:
        失败.append("外部主稿存在完全重复的信息页，应合并或删除：" + "、".join(重复页))

    命中内部 = [w for w in 规则["外部禁用内部表达"] if 纯化(w).lower() in full.lower()]
    if 命中内部:
        失败.append("外部主稿泄漏内部工作台语言：" + "、".join(命中内部))

    元叙事模式 = [
        r"本[页章].{0,8}(?:回答|结论|证明|任务)",
        r"由.{0,16}(?:推出|推导|得出)",
        r"(?:本案|本页|本章).{0,8}(?:推荐|建议采用)",
    ]
    命中元叙事 = [p for p in 元叙事模式 if re.search(p, full)]
    if 命中元叙事:
        失败.append("外部主稿出现汇报过程自述；应直接呈现事实、结论和行动，不写本页回答/推导/推荐标签")

    主稿文字 = "".join(
        visible[i] for i, p in enumerate(pages) if p["section"] != "appendix"
    )
    命中元话语 = [
        w for w in 规则.get("对外元话语风险表达", [])
        if 纯化(w) in 主稿文字
    ]
    if 命中元话语:
        失败.append("外部主稿出现过程说明或空泛收束，应直接写项目对象、证据和结论：" + "、".join(命中元话语))

    命中无主语 = [
        w for w in 规则.get("无主语风险表达", [])
        if 纯化(w) in 主稿文字
    ]
    if 命中无主语:
        失败.append("外部主稿出现隐藏责任主体的表达，应补齐谁、何时、对什么采取何种动作：" + "、".join(命中无主语))

    商业词密集页 = []
    递进词密集页 = []
    标题重复正文页 = []
    for i, (p, t) in enumerate(zip(pages, visible), 1):
        if p["section"] == "appendix":
            continue
        商业词 = 词覆盖(t, 规则.get("空泛商业词", []))
        if len(商业词) >= 3:
            商业词密集页.append(f"{i}（{'、'.join(商业词)}）")
        递进词 = 词覆盖(t, 规则.get("机械递进词", []))
        if len(递进词) >= 4:
            递进词密集页.append(f"{i}（{'、'.join(递进词)}）")
        标题 = 纯化("".join(p["title"]))
        正文 = t.replace(标题, "", 1) if 标题 else t
        if len(标题) >= 10 and 正文.count(标题) >= 1 and len(正文) < 120:
            标题重复正文页.append(i)
    if 商业词密集页:
        失败.append("以下页面空泛商业词过密，需改成主体、动作、对象、指标和结果：" + "；".join(商业词密集页))
    if 递进词密集页:
        失败.append("以下页面使用机械递进串联内容，应按真实因果或决策顺序重写：" + "；".join(递进词密集页))
    if 标题重复正文页:
        失败.append("以下页面正文重复标题且没有补足证据、解释和项目后果：" + "、".join(map(str, 标题重复正文页)))

    对称页段 = []
    起点 = 0
    while 起点 < len(pages):
        卡数 = pages[起点]["cards"]
        终点 = 起点 + 1
        while (
            卡数 in {3, 4}
            and 终点 < len(pages)
            and pages[终点]["section"] != "appendix"
            and pages[终点]["cards"] == 卡数
        ):
            终点 += 1
        if 卡数 in {3, 4} and 终点 - 起点 >= 3:
            对称页段.append(f"{起点 + 1}—{终点}页连续使用{卡数}张卡片")
        起点 = 终点
    if 对称页段:
        失败.append("页面结构连续机械重复；保留真实并列比较，其余改用图表、图纸、原话或单项决策：" + "；".join(对称页段))

    定义式对照模式 = [
        r"(?:不(?:是|只|仅).{0,36}[，,；;。]?\s*而(?:是|更是))",
        r".{1,24}不是问题[，,；;。]?.{0,24}(?:才是|而是).{1,24}问题",
        r"不止.{0,30}(?:更是|更在于|还在于)",
        r"让.{1,24}(?:决定|定义|成就).{1,24}",
    ]
    命中定义式对照 = [p for p in 定义式对照模式 if re.search(p, 主稿文字)]
    if 命中定义式对照:
        失败.append("外部主稿命中模板化的定义式对照句；请改写为人物、场所、动作、数据或结果。")
    正文工作台词 = ["不确定", "待验证", "待核实", "暂定", "备注", "来源待补", "假设", "待补充"]
    命中工作台词 = [w for w in 正文工作台词 if 纯化(w) in 主稿文字]
    if 命中工作台词:
        失败.append("外部正文泄漏待办/不确定性语言，应移入附录：" + "、".join(命中工作台词))
    附录文字 = "".join(visible[i] for i, p in enumerate(pages) if p["section"] == "appendix")
    if not 附录文字:
        失败.append("缺少附录；无法隔离来源口径、资料缺口、估算敏感性与备选排除依据")
    elif not all(w in 附录文字 for w in ["来源", "口径", "资料缺口", "敏感性", "备选"]):
        失败.append("附录未覆盖来源口径、资料缺口、估算敏感性与备选排除依据")
    候选风险 = [w for w in 规则["外部唯一推荐风险词"] if 纯化(w) in 主稿文字]
    if 候选风险:
        失败.append("主稿仍把候选或内部决选交给听众：" + "、".join(候选风险))

    if 类型 == "完整":
        空章节 = [i + 1 for i, p in enumerate(pages) if not p["section"]]
        if 空章节:
            失败.append(
                f"{len(空章节)}页缺少data-section，无法验证外部叙事顺序"
            )
        空主线 = [i + 1 for i, p in enumerate(pages) if not p["proof"]]
        if 空主线:
            失败.append(f"{len(空主线)}页缺少data-proof-node，无法验证主线贯穿")
        空视觉 = [i + 1 for i, p in enumerate(pages) if not p["visual_role"]]
        if 空视觉:
            失败.append(f"{len(空视觉)}页缺少data-visual-role，无法验证页面视觉责任")
        主线集合 = {p["proof"] for p in pages if p["proof"]}
        缺主线 = [x for x in 规则.get("HTML主线节点", []) if x not in 主线集合]
        if 缺主线:
            失败.append("外部主稿未覆盖主线节点：" + "、".join(缺主线))
        角色集合 = {p["visual_role"] for p in pages if p["visual_role"]}
        非法角色 = [x for x in 角色集合 if x not in 规则.get("HTML视觉角色", [])]
        if 非法角色:
            失败.append("存在无效data-visual-role：" + "、".join(非法角色))
        if len(角色集合) < 6:
            失败.append(f"视觉角色仅{len(角色集合)}类，发布会节奏不足")

        counts = Counter(p["section"] for p in pages)
        for section, minimum in 规则["完整外部最少章节页"].items():
            if counts[section] < minimum:
                失败.append(
                    f"章节{section}仅{counts[section]}页，低于完整提案最低责任{minimum}页"
                )

        order = [
            x
            for x in 规则["HTML外部章节顺序"]
            if x != "appendix" and counts[x]
        ]
        positions = [首次位置(pages, x) for x in order]
        for left, right, a, b in zip(
            positions, positions[1:], order, order[1:]
        ):
            if left is not None and right is not None and left > right:
                失败.append(f"章节顺序倒置：{a}出现在{b}之后")

        one_page = [
            i
            for i, p in enumerate(pages)
            if p["prototype"] == 规则["HTML价值体系原型"]
            or "一页纸战略总纲" in visible[i]
        ]
        if not one_page:
            失败.append("缺少前置的一页纸战略总纲")
        elif one_page[0] > 4:
            失败.append(f"一页纸战略总纲位于第{one_page[0]+1}页，应在前5页")

        if not re.search(r"核心概念|精神主张", full):
            失败.append("没有明确标注核心概念/精神主张")
        if "不将就的大盘" in full:
            失败.append("核心表达命中失败回归样本：不将就的大盘")
        概念页 = "".join(
            visible[i] for i, p in enumerate(pages) if p["section"] == "concept"
        )
        命中万能 = [x for x in 规则.get("万能正确句", []) if 纯化(x) in 概念页]
        if 命中万能:
            失败.append("核心表达命中万能正确句，只是企业态度而非项目概念：" + "、".join(命中万能))
        概念责任 = ["购房情境", "两难困境", "项目取舍", "独有做法", "新的比较标准", "可信依据", "客户获得的改变", "成立边界"]
        if len(词覆盖(概念页, 概念责任)) < 6:
            失败.append("概念章节缺少购房情境、人物两难、项目取舍、独有做法、新判断、可信依据或验证状态")

        产品页 = "".join(
            visible[i] for i, p in enumerate(pages) if p["section"] == "product"
        )
        产品词 = [
            "客群", "人物", "面积段", "户型", "房型", "套数", "房间", "公区",
            "尺度", "参数", "成本", "工程", "支付", "去化", "验证", "推荐",
        ]
        产品覆盖 = 词覆盖(产品页, 产品词)
        if len(产品覆盖) < 10:
            失败.append(
                f"产品章节仅覆盖{len(产品覆盖)}/16项客群反推字段，仍可能是通用空间清单"
            )
        情境词 = [
            "竞品关系", "土地能力", "总价", "支付", "货值", "现金流",
            "去化", "供货", "停止条件",
        ]
        if len(词覆盖(产品页, 情境词)) < 7:
            失败.append("产品章节未覆盖土地、竞品、支付、货值、现金流、去化与供货的关键经营约束")
        接口词组 = [
            ["扫地机器人", "扫拖机器人"],
            ["上下水", "给水", "排水"],
            ["插座", "电位"],
            ["检修", "维护"],
            ["网络", "弱电", "AP"],
        ]
        if sum(any(纯化(w) in 产品页 for w in group) for group in 接口词组) < 4:
            失败.append("产品章节缺少消费行为到机电、设备、维护接口的细化")

        推导页 = "".join(
            visible[i] for i, p in enumerate(pages) if p["section"] == "derivation"
        )
        场景词 = ["人物", "时刻", "动作", "物件", "阻碍", "代价", "项目机制", "改变", "验证"]
        if len(词覆盖(推导页, 场景词)) < 7:
            失败.append("价值推导缺少人物、时刻、动作、阻碍、代价、项目机制与改变构成的场景单元")
        文学词 = ["入章情绪", "转折", "离章情绪", "主意象", "事实来源", "前后动作"]
        if len(词覆盖(推导页, 文学词)) < 5:
            失败.append("价值推导缺少情绪变化、转折、项目意象与前后动作对照")

        经营页 = "".join(
            visible[i] for i, p in enumerate(pages) if p["section"] == "economics"
        )
        经营覆盖 = 词覆盖(经营页, 规则["经营必要表达"])
        if len(经营覆盖) < 14:
            失败.append(
                f"经营章节仅覆盖{len(经营覆盖)}/{len(规则['经营必要表达'])}项，成本、利润、现金流或价格推导不完整"
            )
        for group, label in (
            (["总成本", "单位成本", "盈亏平衡"], "成本底线"),
            (["目标利润", "毛利"], "利润"),
            (["现金流安全", "现金流"], "现金流"),
            (["市场可实现", "推荐首开"], "推荐价格"),
        ):
            if not any(纯化(w) in 经营页 for w in group):
                失败.append(f"经营章节缺少{label}说明")

        市场页 = "".join(
            visible[i] for i, p in enumerate(pages) if p["section"] == "market"
        )
        趋势字段 = ["未来12个月", "趋势结论", "分化", "产品后果", "失效信号"]
        if len(词覆盖(市场页, 趋势字段)) < 4:
            失败.append("市场章节缺少有时限、分化对象、产品后果和失效信号的明确趋势结论")
        观察字段 = ["国家统计局", "J.P. Morgan", "趋势动物", "冰山指数"]
        if len(词覆盖(市场页, 观察字段)) < 3:
            失败.append("市场章节未体现官方数据与J.P. Morgan、趋势动物、冰山指数等观察源的交叉验证或不可用说明")

        首开页 = "".join(
            visible[i] for i, p in enumerate(pages) if p["section"] == "launch"
        )
        住宅模式 = len(词覆盖(full, ["住宅", "户型", "认筹", "冻资", "选房"])) >= 2
        if 住宅模式:
            窗口覆盖 = 词覆盖(首开页, 规则["首开必要表达"])
            if len(窗口覆盖) < 8:
                失败.append(
                    f"住宅首开只覆盖{len(窗口覆盖)}/8个时间窗，不能用一页阶段表代替完整战役"
                )
            首开责任 = ["前宣", "样板", "登记", "冻资", "认筹", "选房", "签约", "预算", "负责人", "KPI", "切换信号", "舆情", "应急", "复盘"]
        else:
            首开责任 = ["发布", "样板", "意向", "提案", "签约", "入驻", "预算", "负责人", "KPI", "切换信号", "舆情", "应急", "复盘"]
        if len(词覆盖(首开页, 首开责任)) < 10:
            失败.append("营销章节缺少发布、展示、转化组织、预算责任或复盘")
        阶段组 = 规则.get("全周期营销阶段关键词", [])
        全周期覆盖 = [组[0] for 组 in 阶段组 if any(纯化(w) in 首开页 for w in 组)]
        if len(全周期覆盖) < 12:
            失败.append(f"营销章节只覆盖{len(全周期覆盖)}/12项全周期责任，缺少验证、持续营销、收口或运营")
        动作责任 = ["动作目的", "负责人", "预算", "KPI", "切换信号", "风险", "复盘"]
        if len(词覆盖(首开页, 动作责任)) < 7:
            失败.append("营销章节未写清动作目的、负责人、预算、指标、切换、风险和复盘")
        营销页 = 首开页 + "".join(
            visible[i] for i, p in enumerate(pages) if p["section"] == "media"
        )
        整合责任组 = [
            ["市场阶段", "库存问题"], ["主题承诺", "营销命题"],
            ["搜索", "短视频", "直播"], ["线下验证", "亲手验证"],
            ["圈层关系", "信任来源"], ["私域", "销售承接"],
            ["响应SLA", "响应时限"], ["共同决策", "家庭决策"],
            ["业绩认定", "首触"], ["业主共创", "转介绍"],
        ]
        覆盖责任 = sum(any(纯化(w) in 营销页 for w in group) for group in 整合责任组)
        if 覆盖责任 < 8:
            失败.append(f"营销章节只覆盖{覆盖责任}/10项整合责任，缺少主题、线上、线下、圈层、私域销售或长期运营闭环")
        执行责任 = ["预热内容表", "现场流程表", "人员RACI", "物料清单", "预算拆分", "KPI表", "销售承接", "会后72小时", "应急触发", "加码停止改向"]
        执行覆盖 = 词覆盖(营销页, 执行责任)
        if len(执行覆盖) < 8:
            失败.append(f"营销章节只覆盖{len(执行覆盖)}/10项重点动作执行责任，仍可能只有活动名和一句说明")

        媒介位 = 首次位置(pages, "media")
        概念位 = 首次位置(pages, "concept")
        传播位 = 首次位置(pages, "communication")
        if 媒介位 is not None and (
            概念位 is None or 传播位 is None or 媒介位 < max(概念位, 传播位)
        ):
            失败.append("媒介出现在核心概念/分众传播之前，价值顺序倒置")

        市场位 = 首次位置(pages, "market")
        客群位 = 首次位置(pages, "audience")
        产品位 = 首次位置(pages, "product")
        经营位 = 首次位置(pages, "economics")
        if None not in (市场位, 客群位, 产品位, 经营位, 概念位):
            if not 市场位 < 客群位 < 产品位 < 经营位 < 概念位:
                失败.append("前策顺序倒置：必须市场趋势→消费阶层/行为→产品→经营价格→定位概念")
        身份字段 = ["项目定位", "核心概念", "推广案名", "Slogan"]
        if len(词覆盖(full, 身份字段)) < 4:
            失败.append("未清楚分列项目定位、核心概念、推广案名和Slogan")

    信息短页 = [
        i + 1
        for i, t in enumerate(visible)
        if len(t) < 16
        and pages[i]["section"] != "appendix"
        and pages[i]["prototype"] not in {"cover", "chapter", "section", "end"}
    ]
    if 信息短页:
        失败.append(f"{len(信息短页)}页正文过短，不能作为外部有效页面：" + "、".join(map(str, 信息短页)))

    return list(dict.fromkeys(失败)), list(dict.fromkeys(提醒))


def 自检():
    forbidden = "资料等级审查 · 概念比选审查 · 60个初步方向"
    assert any(w in forbidden for w in 规则["外部禁用内部表达"])
    assert 规则["交付页数"]["完整"] == [70, 120]
    assert 规则["完整外部最少章节页"]["launch"] >= 8
    counts = {
        section: 规则["完整外部最少章节页"][section]
        for section in 规则["HTML外部章节顺序"]
        if section in 规则["完整外部最少章节页"]
    }
    product = "客群人物面积段户型房型套数房间公区尺度参数成本工程支付去化验证竞品关系土地能力总价货值现金流供货停止条件扫拖机器人上下水插座检修弱电AP维护"
    market = "国家统计局J.P. Morgan趋势动物冰山指数未来12个月趋势结论分化产品后果失效信号"
    economics = "".join(规则["经营必要表达"])
    launch = "".join(规则["首开必要表达"]) + "".join(x[0] for x in 规则["全周期营销阶段关键词"]) + "市场阶段库存问题主题承诺营销命题搜索短视频直播线下验证亲手验证圈层关系信任来源私域销售承接响应SLA共同决策家庭决策业绩认定首触业主共创转介绍前宣样板登记冻资认筹选房签约动作目的预算负责人KPI切换信号舆情应急风险复盘预热内容表现场流程表人员RACI物料清单预算拆分KPI表会后72小时应急触发加码停止改向"
    derivation = "人物时刻动作物件阻碍代价项目机制改变验证入章情绪转折离章情绪主意象事实来源前后动作"
    parts = ["<!doctype html><html lang='zh-CN'><meta charset='utf-8'><body>"]
    类型映射 = {
        "opening": "decision", "market": "evidence", "competition": "evidence",
        "project": "product-proof", "audience": "customer-voice", "derivation": "product-proof",
        "product": "product-proof", "economics": "evidence", "concept": "concept",
        "communication": "operation", "media": "operation", "launch": "operation", "execution": "operation",
    }
    index = 0
    for section, number in counts.items():
        for _ in range(number):
            index += 1
            prototype = "value-system" if index == 2 else "content"
            extra = product if section == "product" else economics if section == "economics" else launch if section in {"media", "launch"} else market if section in {"market", "competition"} else derivation if section == "derivation" else ""
            base = f"第{index}项项目事实、方案参数与下一步行动。项目范围为A区216㎡，统计期为2026年7月；与同板块在售样本比较后，该项结论进入后续供货与价格决定。"
            if section == "concept":
                base += "项目定位：完整战略判断。核心概念：精神命题。购房情境与两难困境形成项目取舍、独有做法和新的比较标准；可信依据说明客户获得的改变，并明确成立边界。推广案名：唯一名称。Slogan：阶段传播句。"
            detail = "证据来自已登记资料与同口径样本；本页说明比较差异、成立条件及其对产品、供货和价格安排的具体影响。"
            proof = 规则["HTML主线节点"][min(index - 1, len(规则["HTML主线节点"]) - 1)]
            role = 规则["HTML视觉角色"][(index - 1) % len(规则["HTML视觉角色"])]
            kind = 类型映射[section]
            attrs = (
                f"data-page-kind='{kind}' data-source-id='KDOC-销售统计-20260715' "
                f"data-evidence-id='EV-{index:03d}' data-metric='已核验样本、指标与统计口径' "
                f"data-period='2026年7月' data-comparison-id='同板块在售成交样本' data-chart-id='CH-{index:03d}' "
                f"data-impact='调整对应货包的供货与价格决定' "
                f"data-decision='确认本页对应的项目取舍与执行安排' data-action='项目负责人于2026-08-01完成核验' "
                f"data-owner='项目负责人' data-deadline='2026-08-01' data-artifact='户型图纸与现场照片编号' "
                f"data-quote='受访家庭说明了周中与周末的真实使用变化'"
            )
            parts.append(f"<section class='slide' data-section='{section}' data-proof-node='{proof}' data-prototype='{prototype}' data-visual-role='{role}' {attrs}><h2>{base}</h2><p>{extra}{detail}</p></section>")
    parts.append("<section class='slide' data-section='appendix' data-proof-node='传播与成交' data-prototype='content' data-visual-role='prove'><h2>附录</h2><p>来源口径资料缺口敏感性备选</p></section></body></html>")
    fail, _ = 审查(None, "完整", "".join(parts))
    assert not fail, "合格样本被误拒：" + "；".join(fail)
    bad = "".join(parts).replace("项目事实、方案参数", "概念比选审查 60个初步方向", 1)
    fail_bad, _ = 审查(None, "完整", bad)
    assert any("内部工作台" in x for x in fail_bad), "内部语言泄漏未被识别"
    bad_empty = "".join(parts).replace("第1项项目事实、方案参数与下一步行动", "关键事实：贵不是问题，贵而不可证明才是问题", 1)
    fail_empty, _ = 审查(None, "完整", bad_empty)
    assert any("填页话术" in x for x in fail_empty), "空洞填页话术未被识别"
    bad_contrast = "".join(parts).replace("第2项项目事实、方案参数与下一步行动", "这不是价格问题，而是信任问题", 1)
    fail_contrast, _ = 审查(None, "完整", bad_contrast)
    assert any("定义式对照句" in x for x in fail_contrast), "模板化对照句未被识别"
    bad_meta = "".join(parts).replace("第2项项目事实、方案参数与下一步行动", "本文将从多个维度展开分析，总体来看仍需持续关注", 1)
    fail_meta, _ = 审查(None, "完整", bad_meta)
    assert any("过程说明或空泛收束" in x for x in fail_meta), "元话语和空泛收束未被识别"
    bad_buzz = "".join(parts).replace("第2项项目事实、方案参数与下一步行动", "构建全链路生态闭环，推动价值释放", 1)
    fail_buzz, _ = 审查(None, "完整", bad_buzz)
    assert any("空泛商业词过密" in x for x in fail_buzz), "空泛商业词密集页未被识别"
    bad_passive = "".join(parts).replace("第2项项目事实、方案参数与下一步行动", "项目价值得到提升，空间体验得以实现", 1)
    fail_passive, _ = 审查(None, "完整", bad_passive)
    assert any("隐藏责任主体" in x for x in fail_passive), "无主语判断未被识别"
    bad_frame = "".join(parts).replace("第3项项目事实、方案参数与下一步行动", "四张价格表必须并行", 1)
    fail_frame, _ = 审查(None, "完整", bad_frame)
    assert any("抽象框架" in x for x in fail_frame), "抽象框架页未被识别"
    bad_evidence = "".join(parts).replace(" data-chart-id='CH-004'", "", 1)
    fail_evidence, _ = 审查(None, "完整", bad_evidence)
    assert any("空泛框架页" in x for x in fail_evidence), "无图表或明细表的证据页未被识别"
    bad_marker = "".join(parts).replace(" data-page-kind='decision'", "", 1)
    fail_marker, _ = 审查(None, "完整", bad_marker)
    assert any("没有声明有效页面类型" in x for x in fail_marker), "无页面类型页面未被识别"
    bad_concept = "".join(parts).replace("核心概念：精神命题", "核心概念：不将就的大盘", 1)
    fail_concept, _ = 审查(None, "完整", bad_concept)
    assert any("不将就的大盘" in x for x in fail_concept), "概念失败回归样本未被识别"
    generic_concept = "".join(parts).replace("核心概念：精神命题", "核心概念：每个选择都经得起推敲", 1)
    fail_generic, _ = 审查(None, "完整", generic_concept)
    assert any("万能正确句" in x for x in fail_generic), "万能正确句未被识别"
    shallow = "".join(parts)
    for word in ("预热内容表", "现场流程表", "人员RACI", "物料清单", "预算拆分", "KPI表", "会后72小时", "应急触发", "加码停止改向"):
        shallow = shallow.replace(word, "")
    fail_shallow, _ = 审查(None, "完整", shallow)
    assert any("重点动作执行责任" in x for x in fail_shallow), "营销浅颗粒样本未被识别"
    print("自检通过：合格样本通过；内部泄漏、AI腔结构、失败概念、万能正确句与营销浅颗粒样本均被拒绝。")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("HTML", nargs="?", type=Path)
    ap.add_argument("--类型", choices=["完整", "摘要", "决策", "广告"], default="完整")
    ap.add_argument("--自检", action="store_true")
    args = ap.parse_args()
    if args.自检:
        return 自检()
    if not args.HTML:
        ap.error("请提供HTML路径")
    fail, warn = 审查(args.HTML, args.类型)
    print(f"外部提案审查：{args.HTML}")
    if warn:
        print("\n提醒：")
        for x in warn:
            print("- " + x)
    if fail:
        print("\n未通过：")
        for x in fail:
            print("- " + x)
        return 1
    print("\n通过外部结构初筛；仍须逐页视觉、事实、文学与甲方视角验收。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
