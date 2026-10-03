#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审查前策的上游事实是否足够；客户与产品是推导产物，不是输入门槛。"""
import argparse, json, sys
from pathlib import Path

类别 = ["项目身份", "土地与规划", "市场研究", "竞品研究", "经营约束"]
硬类 = {"项目身份", "土地与规划", "市场研究", "竞品研究"}
兼容映射 = {"市场研究": "市场行为", "竞品研究": "市场行为", "经营约束": "产品边界"}

def 有效项(v):
    if not isinstance(v, dict) or v.get("状态") != "有效": return False
    证据 = v.get("证据")
    return isinstance(证据, list) and len([x for x in 证据 if len(str(x).strip()) >= 6]) >= 1

def main():
    p=argparse.ArgumentParser(); p.add_argument("底稿",type=Path); a=p.parse_args()
    try: d=json.loads(a.底稿.read_text(encoding="utf-8"))
    except Exception as e: print("资料等级审查：无法读取：",e); return 2
    资料=d.get("资料",{})
    def 取项(k): return 资料.get(k) or 资料.get(兼容映射.get(k, ""))
    有效=[k for k in 类别 if 有效项(取项(k))]
    缺=[k for k in 类别 if k not in 有效]
    if 硬类.issubset(有效) and "经营约束" in 有效: 评级="A"
    elif {"项目身份", "土地与规划"}.issubset(有效) and len(有效)>=3: 评级="B"
    else: 评级="C"
    if d.get("评级") and d.get("评级") != 评级:
        print(f"资料等级审查：申报{d.get('评级')}级，自动判定{评级}级，不允许自报升级。")
        return 1
    print(f"资料等级审查：{评级}级；有效{len(有效)}/5：{'、'.join(有效) or '无'}")
    if 缺: print("缺口："+"、".join(缺))
    if 评级=="A": print("允许进入完整故事线；客户、面积段、户型与设计任务书须由前策推导。")
    elif 评级=="B": print("允许客户与产品方向推导及设计任务书；禁止把未核验方向写成已定户型、主概念或案名。")
    else: print("只允许项目识别与研究诊断；先补齐土地规划、市场和竞品调研。")
    return 0 if 评级=="A" else 1
if __name__=="__main__": sys.exit(main())
