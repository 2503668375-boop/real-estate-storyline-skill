#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审查视觉系统是否由项目事实派生，并具备发布会级版式责任。"""
import argparse, json, re, sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
规则 = json.loads((根 / "references" / "统一规则.json").read_text(encoding="utf-8"))
原型 = set(规则["发布会页面原型"])
泛词 = {"高端", "国际", "艺术", "科技", "豪宅", "黑金", "奢华", "高级感"}


def 文本(v):
    return re.sub(r"\s+", "", str(v or "")).strip()


def 有效(v, n=4):
    return len(文本(v)) >= n and 文本(v) not in {"待定", "待核实", "TBD", "-", "—"}


def 审查(d):
    失败 = []
    for k, n in (("项目定位", 8), ("核心概念", 4), ("视觉母体", 4), ("母体事实来源", 10), ("几何语法", 8), ("版面网格", 8), ("图像策略", 8), ("图表语法", 8), ("动效语法", 8), ("章节节奏", 8)):
        if not 有效(d.get(k), n):
            失败.append("缺少有效字段：" + k)
    if 文本(d.get("视觉母体")) in 泛词:
        失败.append("视觉母体仍是通用风格词，必须回到项目事实")
    色 = d.get("主色与语义")
    if not isinstance(色, list) or not 1 <= len(色) <= 3:
        失败.append("主色与语义必须为1—3项")
    else:
        for i, x in enumerate(色, 1):
            if not isinstance(x, dict) or not 有效(x.get("颜色"), 2) or not 有效(x.get("语义"), 4):
                失败.append(f"主色{i}缺少颜色或语义")
    字 = d.get("字体层级")
    if not isinstance(字, list) or not 2 <= len(字) <= 4:
        失败.append("字体层级必须为2—4级")
    页 = d.get("页面原型")
    if not isinstance(页, list):
        失败.append("缺少页面原型")
        页 = []
    命中 = {文本(x.get("名称")) for x in 页 if isinstance(x, dict)} & 原型
    if len(命中) < 8:
        失败.append(f"有效页面原型少于8类（实际{len(命中)}类）")
    for i, x in enumerate(页, 1):
        if not isinstance(x, dict):
            失败.append(f"页面原型{i}不是结构化记录")
            continue
        for k, n in (("名称", 3), ("使用场景", 6), ("视觉重心", 6), ("信息任务", 6)):
            if not 有效(x.get(k), n):
                失败.append(f"页面原型{i}缺少{k}")
    禁 = d.get("禁止项")
    if not isinstance(禁, list) or len(禁) < 5:
        失败.append("禁止项少于5条")
    关键 = d.get("关键页验收")
    必要 = ["封面", "一页纸", "市场证据", "人物代价", "价值推导", "核心概念", "产品", "价格", "全周期营销", "结尾"]
    if not isinstance(关键, list):
        失败.append("缺少关键页验收")
        关键 = []
    全 = "".join(文本(x) for x in 关键)
    for k in 必要:
        if 文本(k) not in 全:
            失败.append("关键页验收缺少：" + k)
    return list(dict.fromkeys(失败))


def 自测样本():
    return {
        "项目定位": "服务明确目标人物的城市更新住宅",
        "核心概念": "让生活重新归位",
        "视觉母体": "城市轴线与旧街巷交叠形成的坐标",
        "母体事实来源": "来自项目总图、城市中轴、街巷方向与人物通勤动作",
        "几何语法": "用轴线、交点、留白和偏移表达现实与生活重新对齐",
        "版面网格": "1920×1080十二栏网格，左右安全区112像素，上下72像素",
        "主色与语义": [{"颜色": "深灰", "语义": "城市底盘"}, {"颜色": "暖白", "语义": "生活主体"}, {"颜色": "朱砂", "语义": "关键选择"}],
        "字体层级": ["大标题", "页标题", "正文", "图注"],
        "图像策略": "优先项目实景、总图、人物真实动作和材料细节，示意图明确标注",
        "图表语法": "统一使用轴线、尺度和位置编码，一张图只表达一个比较基准",
        "动效语法": "只用短距离揭示、因果递进和章节转场，并支持减弱动画",
        "章节节奏": "每三至五页切换页面密度，每八至十二页形成一次小高潮",
        "页面原型": [{"名称": n, "使用场景": "用于对应章节和信息责任", "视觉重心": "一项主证据或主判断", "信息任务": "推动一个不可逆判断"} for n in list(原型)[:8]],
        "禁止项": ["通用黑金", "满页卡片", "连续四页同构", "外网资源", "装饰图库"],
        "关键页验收": ["封面", "一页纸", "市场证据", "人物代价", "价值推导", "核心概念", "产品", "价格", "全周期营销", "结尾"],
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
            print("视觉策略自检：合格样本被误拒")
            for x in 好: print("- " + x)
            return 1
        坏 = json.loads(json.dumps(d, ensure_ascii=False))
        坏["视觉母体"] = "黑金"
        if not any("视觉母体" in x for x in 审查(坏)):
            print("视觉策略自检：通用黑金样本未被拒绝")
            return 1
        print("视觉策略自检：合格样本通过，通用黑金样本被拒绝。")
        return 0
    elif a.底稿:
        try:
            d = json.loads(a.底稿.read_text(encoding="utf-8"))
        except Exception as e:
            print("视觉策略审查：无法读取：", e)
            return 2
    else:
        p.error("必须提供底稿或使用--自检")
    失败 = 审查(d)
    if 失败:
        print("视觉策略审查：未通过")
        for x in 失败:
            print("- " + x)
        return 1
    print("视觉策略审查：通过；项目母体、版式语法、8类原型、节奏与关键页责任完整。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
