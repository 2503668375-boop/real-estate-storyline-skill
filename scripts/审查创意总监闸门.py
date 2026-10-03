#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结构化拦截伪专属、空间臆造、近义发散与自证通过；不替代独立创意判断。"""
import argparse, json, re, sys
from difflib import SequenceMatcher
from pathlib import Path

维度=["土地真实","人物共鸣","取舍鲜明","项目专属","兑现能力","语言感染力","能带出后续动作","有助成交"]
空间词=("环","庭","廊","园","轴","街","谷","岛","厅","桥","塔","院","场")
行政模式=re.compile(r"[A-Z]\d{2,}[-—]\d{2,}|\b\d{3,}\b",re.I)

def 文本(v): return re.sub(r"\s+","",str(v or ""))
def 列表(v): return v if isinstance(v,list) else []

def main():
    p=argparse.ArgumentParser(); p.add_argument("底稿",type=Path); a=p.parse_args()
    try:d=json.loads(a.底稿.read_text(encoding="utf-8"))
    except Exception as e: print("创意总监闸门：无法读取：",e); return 2
    fail=[]
    等级=d.get("资料等级")
    if 等级!="A": fail.append(f"资料等级为{等级 or '未填写'}，不具备确定主概念资格")

    概念=文本(d.get("概念名")); 主张=文本(d.get("主张"))
    if len(概念)<3: fail.append("概念名无效")
    if len(主张)<10: fail.append("主张过短或缺少完整价值判断")
    if 行政模式.search(概念) or any(x in 文本(d.get("主要记忆来源")) for x in ("宗地","编号","数字","道路名")):
        fail.append("概念主要依赖行政编号/数字/道路名形成记忆，属于伪专属")

    if d.get("概念比选审查")!="通过": fail.append("缺少概念比选通过结论")
    if len(文本(d.get("概念比选底稿路径")))<6: fail.append("缺少概念比选底稿路径")
    发散=列表(d.get("创意发散"))
    if len(发散)<60: fail.append(f"创意发散少于60个异质概念种子（实际{len(发散)}）")
    领地={文本(x.get("概念切入角度")) for x in 发散 if isinstance(x,dict) and 文本(x.get("概念切入角度"))}
    if 发散 and len(领地)<12: fail.append(f"概念切入角度少于12类（实际{len(领地)}）")
    方向=[文本(x.get("主张")) for x in 发散 if isinstance(x,dict)]
    for i in range(len(方向)):
        for j in range(i+1,len(方向)):
            if min(len(方向[i]),len(方向[j]))>=6 and SequenceMatcher(None,方向[i],方向[j]).ratio()>=.82:
                fail.append(f"创意方向{i+1}与{j+1}高度近义，不能以换词充数"); break
        if any("高度近义" in x for x in fail): break

    迁移=列表(d.get("换盘测试"))
    if len(迁移)<2: fail.append("缺少至少2个直接竞品换盘测试")
    if any(isinstance(x,dict) and x.get("是否自然成立") is True for x in 迁移):
        fail.append("主张换给直接竞品仍自然成立，不具备项目专属性")

    依据=d.get("空间依据",{}) if isinstance(d.get("空间依据"),dict) else {}
    if any(w in 概念+主张 for w in 空间词) and 依据.get("最新总图") is not True:
        fail.append("概念含空间结构，但没有最新总图支撑，属于空间臆造")

    影响=列表(d.get("产品价格营销影响"))
    if len(影响)<5: fail.append(f"概念可由已定产品/价格/营销结论验证的映射少于5项（实际{len(影响)}）")
    if len(列表(d.get("命名系统")))<3: fail.append("同源命名系统少于3项")
    if len(列表(d.get("三层传播")))<3: fail.append("缺少宏观/中观/微观三层传播")
    if len(列表(d.get("五章战役")))<5: fail.append("连续战役章节少于5章")

    分=d.get("八维评分",{}) if isinstance(d.get("八维评分"),dict) else {}
    if any(k not in 分 for k in 维度): fail.append("八维评分字段不全")
    else:
        try: 数=[float(分[k]) for k in 维度]
        except Exception: 数=[]; fail.append("八维评分必须为数字")
        if 数 and (sum(数)<32 or min(数)<3): fail.append(f"八维评分未达标：总分{sum(数):g}/40，最低{min(数):g}")

    评审=列表(d.get("独立评审")); 角色={文本(x.get("角色")):x for x in 评审 if isinstance(x,dict)}
    for role in ("创意总监","地产经营负责人","苛刻甲方"):
        x=角色.get(role)
        if not x: fail.append(f"缺少隔离评审：{role}")
        elif x.get("结论")!="通过": fail.append(f"独立评审未通过：{role}｜{x.get('结论','未填写')}")

    print(f"创意总监闸门：方向{len(发散)}个；领地{len(领地)}类；影响{len(影响)}项；独立评审{len(评审)}个")
    if fail:
        print("\n不通过：")
        for x in dict.fromkeys(fail): print("- "+x)
        return 1
    print("\n自动结构与三重独立审查通过；仍须由最终决策者审看真实创意质量。")
    return 0
if __name__=="__main__": sys.exit(main())
