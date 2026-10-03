#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审查8.1内部传播与首开底稿的完整执行责任。"""
import argparse, json, re, sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
规则 = json.loads((根 / "references" / "统一规则.json").read_text(encoding="utf-8"))
禁活动 = 规则["禁止通用活动"]
渠道表 = 规则.get("媒介渠道", [])


def 文本(v):
    return re.sub(r"\s+", "", v.strip()) if isinstance(v, str) else ""


def 片段集(s, 最短=2):
    """概念名的全部连续片段（长度≥最短）。"""
    return {s[i:i + n] for n in range(最短, len(s) + 1) for i in range(0, len(s) - n + 1)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("经营", type=Path)
    p.add_argument("--故事线", type=Path, required=True)
    a = p.parse_args()
    try:
        d = json.loads(a.经营.read_text(encoding="utf-8"))
        s = json.loads(a.故事线.read_text(encoding="utf-8"))
    except Exception as e:
        print("营销媒介关：无法读取底稿：", e); return 2
    失败 = []

    营销 = d.get("产品预判营销", {})
    战役 = 营销.get("首开战役")
    if not isinstance(战役, list) or len(战役) < 8:
        失败.append(f"首开战役不足8个时间窗（实际{len(战役) if isinstance(战役, list) else 0}个）")
        战役 = 战役 if isinstance(战役, list) else []

    for i, x in enumerate(战役, 1):
        if not isinstance(x, dict):
            失败.append(f"时间窗{i}不是结构化记录"); continue
        名 = x.get("时间窗", f"第{i}窗")
        if len(文本(x.get("验证承诺"))) < 6:
            失败.append(f"时间窗「{名}」缺少验证承诺字段（≥6字）")
        for k in ("主受众","信念任务","核心信息","线上动作","线下动作","案场渠道","货量价格","预算","负责人","KPI","切换信号","风险"):
            if len(文本(x.get(k))) < 2:
                失败.append(f"时间窗「{名}」缺少{k}")
        全文 = json.dumps(x, ensure_ascii=False)
        for 禁 in 禁活动:
            if 禁 in 全文 and len(文本(x.get("必要性说明"))) < 10:
                失败.append(f"时间窗「{名}」命中禁止通用活动「{禁}」且无≥10字必要性说明")

    亲手 = sum(1 for x in 战役 if isinstance(x, dict) and x.get("客户亲手验证") is True)
    if 亲手 < 3:
        失败.append(f"客户亲手验证时刻少于3个时间窗（实际{亲手}个）")
    实际窗口={文本(x.get("时间窗")) for x in 战役 if isinstance(x,dict)}
    for w in 规则.get("首开时间窗",[]):
        if 文本(w) not in 实际窗口:
            失败.append("缺少标准首开时间窗："+w)

    概念名 = 文本(s.get("概念新颖性", {}).get("概念名"))
    if not 概念名:
        失败.append("故事线底稿缺少概念新颖性.概念名，无法校验调性一致性")
    else:
        片段 = 片段集(概念名)
        命中 = sum(
            1 for x in 战役 if isinstance(x, dict)
            and any(g in (文本(x.get("核心信息")) + 文本(x.get("线下动作"))) for g in 片段))
        if 命中 < 3:
            失败.append(f"少于3个时间窗的核心信息或线下动作含概念名「{概念名}」的连续片段（实际{命中}个）")

    矩阵 = 营销.get("媒介传播矩阵")
    覆盖 = 0
    if not isinstance(矩阵, dict) or not 矩阵:
        失败.append("产品预判营销缺少「媒介传播矩阵」区块")
        矩阵 = {}
    for 渠道, 项 in 矩阵.items():
        if not isinstance(项, dict):
            失败.append(f"媒介渠道「{渠道}」不是结构化记录"); continue
        缺 = []
        if len(文本(项.get("目标与打法"))) < 8: 缺.append("目标与打法≥8字")
        if len(文本(项.get("节奏"))) < 4: 缺.append("节奏≥4字")
        if len(文本(项.get("衡量指标"))) < 4: 缺.append("衡量指标≥4字")
        if 缺:
            失败.append(f"媒介渠道「{渠道}」缺：{'、'.join(缺)}")
        else:
            覆盖 += 1
    if 渠道表:
        白名单命中 = sum(1 for c in 矩阵 if any(c in k or k in c for k in 渠道表))
        if 覆盖 < 6:
            失败.append(f"媒介传播矩阵合格渠道少于6个（实际{覆盖}个），渠道清单见统一规则.json「媒介渠道」")
        elif 白名单命中 < 覆盖:
            失败.append("媒介渠道名须使用统一规则.json「媒介渠道」的标准名称")

    if 失败:
        print("营销媒介关：未通过"); [print("- " + x) for x in dict.fromkeys(失败)]; return 1
    print(f"营销媒介关：通过；{len(战役)}个时间窗全部带验证承诺，{亲手}个为客户亲手验证时刻；媒介矩阵覆盖{覆盖}个渠道。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
