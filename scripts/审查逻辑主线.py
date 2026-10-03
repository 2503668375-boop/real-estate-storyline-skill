#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审查主线是否为可证伪因果，并形成跨章证明合同。"""
import argparse, json, re, sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
规则 = json.loads((根 / "references" / "统一规则.json").read_text(encoding="utf-8"))
节点 = 规则["逻辑主线节点"]
占位 = {"", "待定", "待核实", "TBD", "-", "—", "高端", "品质", "稀缺", "唯一"}


def 文本(v):
    return re.sub(r"\s+", "", str(v or "")).strip()


def 有效(v, n=8):
    return len(文本(v)) >= n and 文本(v) not in 占位


def 审查(d):
    失败 = []
    if not 有效(d.get("主线命题"), 36):
        失败.append("主线命题少于36个有效字符，或仍是口号")
    for k, n in (("反命题", 10), ("成立边界", 10), ("可证伪条件", 10), ("90秒管理层复述", 30), ("30秒销售讲法", 24), ("全周期营销总主题", 8)):
        if not 有效(d.get(k), n):
            失败.append("缺少有效字段：" + k)

    表 = d.get("主线节点")
    if not isinstance(表, dict):
        失败.append("缺少主线节点对象")
        表 = {}
    for 名 in 节点:
        x = 表.get(名)
        if not isinstance(x, dict):
            失败.append("缺少主线节点：" + 名)
            continue
        for k, n in (("上游依据", 10), ("本节点结论", 10), ("人物动作或感受", 8), ("排除的旧选项", 8), ("下游决定", 8), ("证据与状态", 8), ("成立边界", 6)):
            if not 有效(x.get(k), n):
                失败.append(f"主线节点「{名}」缺少{k}")

    合同 = d.get("章节证明合同")
    if not isinstance(合同, list) or len(合同) < 10:
        失败.append(f"章节证明合同少于10张（实际{len(合同) if isinstance(合同, list) else 0}张）")
        合同 = 合同 if isinstance(合同, list) else []
    覆盖 = set()
    for i, x in enumerate(合同, 1):
        if not isinstance(x, dict):
            失败.append(f"章节证明合同{i}不是结构化记录")
            continue
        名 = 文本(x.get("主线节点"))
        if 名 not in 节点:
            失败.append(f"章节证明合同{i}引用无效节点：{名 or '空'}")
        else:
            覆盖.add(名)
        for k, n in (("章节", 2), ("开章未解问题", 8), ("新增证据", 8), ("章末结论", 8), ("排除的旧选项", 8), ("下一章问题", 8), ("删除后断点", 8)):
            if not 有效(x.get(k), n):
                失败.append(f"章节证明合同{i}缺少{k}")
    if len(覆盖) < 10:
        失败.append(f"章节证明合同仅覆盖{len(覆盖)}/10个主线节点")

    同源 = d.get("同源校验")
    if not isinstance(同源, dict):
        失败.append("缺少同源校验")
        同源 = {}
    for k in ("一页纸", "标题链", "销售讲法", "全周期营销"):
        if not 有效(同源.get(k), 10):
            失败.append("同源校验缺少：" + k)

    反向 = d.get("反向校验")
    if not isinstance(反向, dict):
        失败.append("缺少反向校验")
        反向 = {}
    for k in ("删概念", "换项目", "删章", "产品", "价格", "营销", "复述", "证伪"):
        if not 有效(反向.get(k), 8):
            失败.append("反向校验缺少：" + k)
    return list(dict.fromkeys(失败))


def 自测样本():
    节点表 = {}
    for i, 名 in enumerate(节点):
        节点表[名] = {
            "上游依据": f"第{i+1}组已核验事实与人物行为证据",
            "本节点结论": f"{名}必须改变项目的下一项选择",
            "人物动作或感受": "目标家庭在真实比较与决策时感到代价被说破",
            "排除的旧选项": "排除只叠加资源和通用豪宅配置的旧答案",
            "下游决定": "进入下一节点并形成明确产品经营后果",
            "证据与状态": "项目材料与外部来源交叉核验，状态为已核验",
            "成立边界": "仅在目标客户、价格与规划边界内成立",
        }
    合同 = [{
        "章节": f"第{i+1}章", "主线节点": 名,
        "开章未解问题": "听众尚未相信该节点为何必须成立",
        "新增证据": "本章新增事实、人物动作与可指认证据",
        "章末结论": "本章完成不可逆判断并形成唯一选择",
        "排除的旧选项": "排除一个行业旧答案与无效比较",
        "下一章问题": "下一章必须证明这一选择如何继续兑现",
        "删除后断点": "删除本章会导致上游事实无法推出下游决定",
    } for i, 名 in enumerate(节点)]
    return {
        "主线命题": "因为外部现实让目标家庭持续付出具体代价，而市场仍用旧答案回应，所以项目必须做出明确取舍并用可验证机制改变生活与经营结果。",
        "反命题": "项目不以更多配置和更大声量代替真实机制",
        "成立边界": "只在目标客户、规划条件、成本和市场证据成立时采用",
        "可证伪条件": "关键客户行为、规划或价格证据改变时必须撤回",
        "90秒管理层复述": "从现实变化、人物代价、竞争失效走到战略取舍，再用产品价格传播和成交结果连续证明。",
        "30秒销售讲法": "因为事实如此，所以项目不做旧答案；它用三项真实机制让客户获得可感知改变。",
        "全周期营销总主题": "让同一价值从被看见走到被兑现",
        "主线节点": 节点表,
        "章节证明合同": 合同,
        "同源校验": {k: "与主线命题保持同一事实、人物、取舍和兑现关系" for k in ("一页纸", "标题链", "销售讲法", "全周期营销")},
        "反向校验": {k: "已执行测试并记录断点、结论与必要调整" for k in ("删概念", "换项目", "删章", "产品", "价格", "营销", "复述", "证伪")},
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("底稿", type=Path, nargs="?")
    p.add_argument("--自检", action="store_true")
    a = p.parse_args()
    if a.自检:
        d = 自测样本()
        好 = 审查(d)
        if 好:
            print("逻辑主线自检：合格样本被误拒")
            for x in 好: print("- " + x)
            return 1
        坏 = json.loads(json.dumps(d, ensure_ascii=False))
        坏["主线节点"].pop("价格证明")
        if not any("价格证明" in x for x in 审查(坏)):
            print("逻辑主线自检：缺节点样本未被拒绝")
            return 1
        print("逻辑主线自检：合格样本通过，缺节点样本被拒绝。")
        return 0
    elif a.底稿:
        try:
            d = json.loads(a.底稿.read_text(encoding="utf-8"))
        except Exception as e:
            print("逻辑主线审查：无法读取：", e)
            return 2
    else:
        p.error("必须提供底稿或使用--自检")
    失败 = 审查(d)
    if 失败:
        print("逻辑主线审查：未通过")
        for x in 失败:
            print("- " + x)
        return 1
    print("逻辑主线审查：通过；十节点、章节证明合同、四处同源与八项反向校验完整。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
