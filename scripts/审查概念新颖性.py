#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审查6.9概念新颖性：概念指纹、警戒词、竞品避让与共鸣。"""
import argparse, json, re, sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
规则 = json.loads((根 / "references" / "统一规则.json").read_text(encoding="utf-8"))
警戒词 = 规则["高频警戒词"]
万能正确句 = 规则.get("万能正确句", [])
行政模式 = re.compile(r"[A-Z]\d{2,}[-—]\d{2,}|\b\d{3,}\b", re.I)
# 与 审查故事线母题.py 保持同一泛母题逻辑
泛母题 = {"美好生活", "理想生活", "向往生活", "从容生活", "松弛生活", "时代作品", "城市封面", "未来生活"}


def 文本(v):
    return re.sub(r"\s+", "", v.strip()) if isinstance(v, str) else ""


def 命中数(s):
    return sum(1 for w in 警戒词 if w in s)


def 是万能正确句(s):
    return any(文本(x) in s for x in 万能正确句) or bool(
        re.search(r"(?:每个|每一次|每一步).{0,10}都|经得起(?:推敲|时间|检验|考验)", s)
    )


def main():
    p = argparse.ArgumentParser(); p.add_argument("底稿", type=Path); a = p.parse_args()
    try:
        d = json.loads(a.底稿.read_text(encoding="utf-8"))
    except Exception as e:
        print("概念审查关：无法读取底稿：", e); return 2
    失败 = []

    块 = d.get("概念新颖性")
    if not isinstance(块, dict):
        失败.append("缺少概念新颖性区块"); 块 = {}

    概念名 = 文本(块.get("概念名"))
    if len(概念名) < 3:
        失败.append("概念名少于3字")

    tokens = 块.get("事实token")
    if not isinstance(tokens, list) or not tokens:
        失败.append("事实token必须为至少1项的列表")
        tokens = []
    if 行政模式.search(概念名):
        失败.append("概念名直接使用宗地号/行政编号制造专属感，token不能替代思想价值")
    if len(文本(块.get("独有意义"))) < 12:
        失败.append("缺少独有意义：须说明这块地为何只能产生这一价值判断")
    if len(文本(块.get("意外解释"))) < 12:
        失败.append("缺少意外解释：只有事实独有而理解普通，仍然不新颖")
    if len(文本(块.get("改写的比较标准"))) < 12:
        失败.append("缺少改写的比较标准：正确态度不能代替新的项目判断")

    避让 = 块.get("竞品口号避让")
    if not isinstance(避让, list) or len(避让) < 2:
        失败.append("竞品口号避让少于2条")
    else:
        for i, x in enumerate(避让, 1):
            if not isinstance(x, dict) or any(not 文本(x.get(k)) for k in ("竞品", "口号", "避让理由")):
                失败.append(f"竞品口号避让{i}字段不全（竞品/口号/避让理由）")

    if len(文本(块.get("陌生化测试"))) < 10:
        失败.append("陌生化测试少于10字：须写清换给哪个竞品、为何不成立")
    if len(文本(块.get("客户原声或行为矛盾"))) < 12:
        失败.append("客户原声或行为矛盾少于12字：行为证据优先于话语")

    if 命中数(概念名) >= 2:
        失败.append(f"概念名命中高频警戒词{命中数(概念名)}个（≥2即淘汰）：{概念名}")
    if 是万能正确句(概念名):
        失败.append("概念名命中万能正确句，只是企业态度而非项目概念")

    主命题 = 文本(d.get("精神母题", {}).get("主命题"))
    if 主命题:
        if 命中数(主命题) >= 2:
            失败.append(f"主命题命中高频警戒词{命中数(主命题)}个（允许至多1个）：{主命题}")
        if 主命题 in 泛母题:
            失败.append("主命题为可替换泛母题，必须从项目事实重做")
        if 是万能正确句(主命题):
            失败.append("主命题命中万能正确句，没有项目占有性、人物画面与新判断")

    if 失败:
        print("概念审查关：未通过"); [print("- " + x) for x in dict.fromkeys(失败)]; return 1
    print(f"概念审查关：结构通过；概念名「{概念名}」具备独有意义、意外解释与新比较标准，仍须独立创意终审。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
