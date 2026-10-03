#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审查6.9阶段0研究底稿：五层检索是否覆盖、口径是否干净。"""
import argparse, json, re, sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
规则 = json.loads((根 / "references" / "统一规则.json").read_text(encoding="utf-8"))
级别 = 规则["来源可信级别"]
联网枚举 = {"可用", "不可用", "结果为空", "来源冲突"}
五层 = ["城市", "板块", "竞品", "客户", "项目"]


def 文本(v):
    return re.sub(r"\s+", "", v.strip()) if isinstance(v, str) else ""


def main():
    p = argparse.ArgumentParser(); p.add_argument("底稿", type=Path); a = p.parse_args()
    try:
        d = json.loads(a.底稿.read_text(encoding="utf-8"))
    except Exception as e:
        print("研究审查关：无法读取底稿：", e); return 2
    失败 = []

    if d.get("联网状态") not in 联网枚举:
        失败.append("联网状态必须为：" + "、".join(sorted(联网枚举)))

    表 = d.get("事实表")
    if not isinstance(表, list) or len(表) < 10:
        失败.append(f"事实表少于10条（实际{len(表) if isinstance(表, list) else 0}条）")
        表 = 表 if isinstance(表, list) else []

    for i, x in enumerate(表, 1):
        if not isinstance(x, dict):
            失败.append(f"事实{i}不是结构化记录"); continue
        if len(文本(x.get("指标"))) < 2: 失败.append(f"事实{i}指标无效")
        if not 文本(str(x.get("数值", ""))): 失败.append(f"事实{i}数值为空")
        if len(文本(str(x.get("时间", "")))) < 4: 失败.append(f"事实{i}时间无效")
        if len(文本(x.get("来源"))) < 4: 失败.append(f"事实{i}来源无效")
        if x.get("可信级别") not in 级别: 失败.append(f"事实{i}可信级别不在八级枚举内")
        if len(文本(x.get("对决策影响"))) < 8: 失败.append(f"事实{i}缺少对决策影响")

    覆盖 = {文本(x.get("层级")) for x in 表 if isinstance(x, dict)}
    for 层 in 五层:
        if 层 not in 覆盖: 失败.append(f"五层检索缺少：{层}层")

    if not any(isinstance(x, dict) and re.search(r"开盘|去化|备案", 文本(x.get("来源"))) for x in 表):
        失败.append("缺少至少1条竞品开盘证据（来源须含开盘/去化/备案）")

    权威 = sum(1 for x in 表 if isinstance(x, dict) and x.get("可信级别") in {"政府交易", "规划公告", "权威媒体"})
    if 权威 < 2:
        失败.append(f"政府交易/规划公告/权威媒体级来源合计少于2条（实际{权威}条）")

    if 失败:
        print("研究审查关：未通过"); [print("- " + x) for x in dict.fromkeys(失败)]; return 1
    print(f"研究审查关：通过；事实表{len(表)}条，五层覆盖完整，允许进入故事线导演。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
