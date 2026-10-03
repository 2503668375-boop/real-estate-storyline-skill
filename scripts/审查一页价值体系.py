#!/usr/bin/env python3
"""审查一页纸JSON，并生成可供PPT、HTML、PDF共同引用的内容指纹。"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
规则 = json.loads((根/"references"/"统一规则.json").read_text(encoding="utf-8"))

def 字数(v): return len(re.sub(r"\s+", "", str(v or "")))
def 非空(v): return isinstance(v, str) and v.strip() not in {"", "待定", "待核实", "TBD", "—", "-"}
def 指纹(d):
    副本 = dict(d); 副本.pop("内容指纹", None)
    原文 = json.dumps(副本, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(原文).hexdigest()

def 主程序():
    p=argparse.ArgumentParser(); p.add_argument("文件",type=Path); p.add_argument("--密度",choices=("现场","阅读"),default="阅读"); p.add_argument("--写入指纹",action="store_true"); a=p.parse_args()
    try: d=json.loads(a.文件.read_text(encoding="utf-8",errors="strict"))
    except Exception as e: print(f"硬失败：{e}"); return 2
    fp=指纹(d)
    if a.写入指纹:
        d["内容指纹"]=fp
        a.文件.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    失败=[]; 警告=[]
    for k in ("项目名称","底稿编号","页面标题","核心判断"):
        if not 非空(d.get(k)): 失败.append("缺少有效字段："+k)
    for k in ("决策问题","关键矛盾","推荐定位","核心概念","目标客群","产品答案","价格与经营","传播与首开"):
        if not 非空(d.get(k)): 失败.append("一页纸战略总纲缺少："+k)
    风险=d.get("风险与批准")
    if not isinstance(风险,(dict,list)) or not 风险:
        失败.append("一页纸战略总纲缺少：风险与批准")
    if d.get("内容指纹") != fp: 失败.append("内容指纹缺失或与当前底稿不一致；请使用--写入指纹")
    for k,n in 规则["一页字段上限"].items():
        v=d.get(k)
        for 分组 in ("战略枢纽","四项定位","创意概念"):
            if not 非空(v) and isinstance(d.get(分组),dict): v=d[分组].get(k)
        if v is not None and 字数(v)>n: 失败.append(f"{k}超过{n}字")
    发现=d.get("价值发现",[])
    if not isinstance(发现,list) or len(发现)!=3: 失败.append("价值发现必须恰好3项")
    支柱=d.get("价值支柱",[])
    if not isinstance(支柱,list) or not 3<=len(支柱)<=5: 失败.append("价值支柱必须3—5项")
    for i,x in enumerate(支柱,1):
        if not isinstance(x,dict) or not all(非空(x.get(k)) for k in ("名称","事实证据","产品动作")): 失败.append(f"价值支柱{i}缺少名称、事实证据或产品动作")
    传播=d.get("传播层次",[])
    if {x.get("层级") for x in 传播 if isinstance(x,dict)} != {"宏观","中观","微观"}: 失败.append("传播层次必须为宏观、中观、微观")
    阶段=d.get("阶段铺排",[])
    if not isinstance(阶段,list) or not 3<=len(阶段)<=5: 失败.append("阶段铺排必须3—5项")
    批准=d.get("需批准事项",[])
    下限,上限=规则["需批准事项数量"]
    if not isinstance(批准,list) or not 下限<=len(批准)<=上限 or not all(非空(x) for x in 批准): 失败.append(f"需批准事项必须为{下限}—{上限}项")
    来源=d.get("来源说明",[])
    if not isinstance(来源,list) or not 来源: 失败.append("缺少来源说明")
    不计={"来源说明","需批准事项","内容指纹"}
    def 累计(o,k=""):
        if k in 不计:return 0
        if isinstance(o,dict): return sum(累计(v,kk) for kk,v in o.items())
        if isinstance(o,list): return sum(累计(v,k) for v in o)
        return 字数(o)
    可见=累计(d); 上限=450 if a.密度=="现场" else 800
    if 可见>上限: 失败.append(f"可见文字约{可见}字，超过{a.密度}版{上限}字")
    print(f"一页纸审查：来源{len(发现)}；支柱{len(支柱)}；阶段{len(阶段)}；可见{可见}字")
    print("内容指纹："+fp)
    if 失败:
        print("\n硬失败：")
        for x in dict.fromkeys(失败): print("- "+x)
    else: print("\n通过结构与同源审查；仍须视觉验收。")
    return 1 if 失败 else 0
if __name__=="__main__": sys.exit(主程序())
