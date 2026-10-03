#!/usr/bin/env python3
"""按统一规则审查住宅前策文本的数字、客户、情境、母题与引文。"""

from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

根目录 = Path(__file__).resolve().parents[1]
规则 = json.loads((根目录 / "references" / "统一规则.json").read_text(encoding="utf-8"))
必需章节 = ["市场", "竞品", "客户", "预判", "定位", "户型", "价格", "营销"]
价格模式 = r"\d[\d,]*(?:\.\d+)?(?:\s*(?:—|-|至|~)\s*\d[\d,]*(?:\.\d+)?)?\s*(?:万元?|万|元)\s*/\s*(?:㎡|m²|m2|m\^2|平方米|平米)"

def 分块(文本: str) -> list[str]:
    return [块 for 块 in re.split(r"\n\s*\n|(?=^#{1,6}\s)", 文本, flags=re.M) if 块.strip()]

def 精确母题卡(文本: str) -> tuple[int, list[str]]:
    卡片 = []
    for 块 in 分块(文本):
        if "母题资格审查" in 块:
            卡片.append(块)
    合格 = []
    for 卡 in 卡片:
        字段齐 = all(字段 in 卡 for 字段 in 规则["母题资格字段"])
        精确通过 = bool(re.search(r"(?m)^\s*审查结论\s*[：:]\s*通过\s*$", 卡))
        影响 = re.search(r"产品价格营销影响\s*[：:](.*)", 卡)
        三项 = bool(影响 and len([x for x in re.split(r"[、，,；;]", 影响.group(1)) if x.strip()]) >= 3)
        if 字段齐 and 精确通过 and 三项:
            合格.append(卡)
    return len(合格), 卡片

def 主程序() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("文件", type=Path)
    a = p.parse_args()
    if not a.文件.is_file():
        print("硬失败：文件不存在")
        return 2
    try:
        文本 = a.文件.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        print("硬失败：文件不是有效UTF-8")
        return 2
    纯文 = re.sub(r"<[^>]+>", " ", 文本)
    失败, 警告 = [], []

    价格 = set(re.findall(价格模式, 纯文, re.I))
    if len(价格) < 3: 失败.append("少于3组可识别的元/㎡、万元/㎡或万/m²数字价格")
    if not ("首开" in 纯文 and "成交" in 纯文): 失败.append("缺少首开成交价格口径")
    if any(x not in 纯文 for x in 必需章节): 失败.append("缺少核心内容：" + "、".join(x for x in 必需章节 if x not in 纯文))

    面积行 = [行 for 行 in 纯文.splitlines() if re.search(r"\d{2,3}(?:\.\d+)?\s*(?:—|-|至|~)?\s*\d{0,3}(?:\.\d+)?\s*(?:㎡|m²|平方米|平米)", 行)]
    配比行 = [行 for 行 in 面积行 if len(re.findall(r"\d+(?:\.\d+)?\s*%", 行)) >= 2 and re.search(r"\d+\s*套", 行)]
    if len(配比行) < 3: 失败.append("少于3个同时含面积、面积占比、套数占比和预计套数的户型分项")
    else:
        面积占比 = [float(re.findall(r"(\d+(?:\.\d+)?)\s*%", 行)[0]) for 行 in 配比行]
        套数占比 = [float(re.findall(r"(\d+(?:\.\d+)?)\s*%", 行)[1]) for 行 in 配比行]
        if abs(sum(面积占比)-100) > .2: 失败.append(f"面积占比合计{sum(面积占比):g}%，不等于100%")
        if abs(sum(套数占比)-100) > 1.5: 失败.append(f"套数占比合计{sum(套数占比):g}%，不在允许误差")
    if not re.search(r"计算基数.{0,30}\d[\d,]*(?:\.\d+)?\s*(?:万)?\s*(?:㎡|m²|平方米|平米)", 纯文): 失败.append("缺少户型计算基数")
    if not re.search(r"总套数.{0,20}\d+\s*套", 纯文): 失败.append("缺少总套数")

    for 情境 in 规则["三情境"]:
        合格块 = [块 for 块 in 分块(纯文) if 情境 in 块 and re.search(价格模式, 块, re.I) and ("配比" in 块 or "套数" in 块) and "首推" in 块 and ("触发" in 块 or "切换" in 块)]
        if not 合格块: 失败.append(f"{情境}情境缺少同一段落或表格块内的数字价格、配比/套数、首推和触发信号")

    客户块 = [块 for 块 in 分块(纯文) if re.search(r"客户决策卡\s*\d+", 块)]
    字段 = 规则["住宅客户卡字段"]
    def 客户合格(块):
        资产合格 = "现居与持有资产" in 块 or "现有资产" in 块
        其余 = [x for x in 字段 if x != "现居与持有资产"]
        return 资产合格 and all(x in 块 for x in 其余) and bool(re.search(r"\d[\d,]*\s*万", 块))
    if sum(客户合格(x) for x in 客户块) < 3: 失败.append("少于3张字段齐全且含数字资金或总价的客户决策卡")

    for 窗口 in 规则["首开时间窗"]:
        if 窗口 not in 纯文: 失败.append(f"缺少首开时间窗：{窗口}")
    for 字段名 in ("线索", "到访", "复访", "认筹", "认购"):
        if not re.search(rf"{字段名}.{{0,40}}\d+", 纯文): 失败.append(f"漏斗缺少数字：{字段名}")
    for 字段名 in ("预算", "负责人"):
        if 字段名 not in 纯文: 失败.append(f"首开倒排缺少：{字段名}")

    词频 = {词: 纯文.count(词) for 词 in 规则["常用母题词"]}
    总数 = sum(词频.values())
    密度 = 总数 * 1000 / max(len(re.sub(r"\s+", "", 纯文)), 1)
    合格卡数, 所有卡 = 精确母题卡(纯文)
    if (总数 >= 50 or 密度 >= 8) and not 合格卡数:
        失败.append(f"母题词密度过高且没有字段齐全、精确判定为通过的母题卡：{总数}次")
    if 所有卡 and not 合格卡数: 失败.append("发现母题资格审查卡，但字段、三项影响或精确结论不合格")
    for 词, 次数 in 词频.items():
        if 次数 >= 12 and not 合格卡数: 失败.append(f"“{词}”高频出现{次数}次且未通过统一母题资格审查")

    署名 = list(re.finditer(r"“[^”]{2,120}”\s*[-—]{1,2}\s*[\u4e00-\u9fffA-Za-z·. ]{2,40}", 纯文))
    for 引 in 署名:
        附近 = 纯文[max(0, 引.start()-500):min(len(纯文), 引.end()+500)]
        if not all(x in 附近 for x in 规则["引文核验字段"]):
            失败.append("署名引文附近缺少已核验、原文出处或核验日期")
            break

    if re.search(r"(?:价格|配比).{0,16}(?:无法给出|暂不提供|待后续确定|待定)", 纯文): 失败.append("以资料不足或待定逃避具体价格配比")
    print(f"住宅前策审查：价格{len(价格)}组；户型分项{len(配比行)}；客户卡{sum(客户合格(x) for x in 客户块)}；母题卡{合格卡数}")
    if 失败:
        print("\n硬失败：")
        for x in dict.fromkeys(失败): print("- " + x)
    if 警告:
        print("\n警告：")
        for x in dict.fromkeys(警告): print("- " + x)
    if not 失败: print("\n通过自动底线审查；仍须人工核验事实、逻辑与视觉。")
    return 1 if 失败 else 0

if __name__ == "__main__": sys.exit(主程序())

