#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拦截历史符号拼贴、全人群同话术和只有渠道没有信念改变的传播底稿。"""
import argparse, json, re, sys
from pathlib import Path

占位={"","待定","待核实","TBD","-","—","高净值","精英","高知","圈层"}
章节={"看见","认出","相信","参与","见证"}
受众类={"核心购买者","家庭共同决策者","市场解释者","文化/社群种子"}

def 文本(v): return re.sub(r"\s+","",str(v or "")).strip()
def 有效(v,n=6): return len(文本(v))>=n and 文本(v) not in 占位
def 列表(v): return v if isinstance(v,list) else []

def main():
    p=argparse.ArgumentParser(); p.add_argument("底稿",type=Path); a=p.parse_args()
    try:d=json.loads(a.底稿.read_text(encoding="utf-8"))
    except Exception as e: print("人文传播关：无法读取：",e); return 2
    fail=[]
    concept=d.get("人文概念",{}) if isinstance(d.get("人文概念"),dict) else {}
    for k,n in (("概念",3),("地方或时代事实",10),("当代矛盾",12),("项目立场",10),("生活实践",12),("公共意义",10),("失败边界",8)):
        if not 有效(concept.get(k),n): fail.append("人文概念缺少有效字段："+k)

    aud=列表(d.get("受众翻译")); found=set()
    if len(aud)<4: fail.append(f"受众翻译少于4类（实际{len(aud)}）")
    for i,x in enumerate(aud,1):
        if not isinstance(x,dict): fail.append(f"受众卡{i}不是结构化卡片"); continue
        kind=文本(x.get("受众类型"))
        if kind not in 受众类: fail.append(f"受众卡{i}类型无效：{kind or '未填写'}")
        else: found.add(kind)
        for k,n in (("受众",4),("已有信念",8),("隐性焦虑",8),("期望身份",6),("证据门槛",8),
                    ("主信息",8),("内容母题",8),("可信讲述者",4),("触达场景",6),("行动",4),("指标",4)):
            if not 有效(x.get(k),n): fail.append(f"受众卡{i}缺少有效字段：{k}")
    missing=受众类-found
    if missing: fail.append("缺少受众类型："+ "、".join(sorted(missing)))
    messages=[文本(x.get("主信息")) for x in aud if isinstance(x,dict)]
    if len(messages)>=4 and len(set(messages))<3: fail.append("不同受众重复同一主信息，属于只换渠道不换信念逻辑")

    content=列表(d.get("内容五章")); got=set()
    if len(content)<5: fail.append(f"内容章节少于5章（实际{len(content)}）")
    for i,x in enumerate(content,1):
        if not isinstance(x,dict): fail.append(f"内容章节{i}不是结构化卡片"); continue
        name=文本(x.get("章节"))
        if name not in 章节: fail.append(f"内容章节{i}名称无效：{name or '未填写'}")
        else: got.add(name)
        for k,n in (("要改变的旧认知",8),("核心证据",8),("人物故事",8),("内容载体",4),("可信讲述者",4),("承接动作",4)):
            if not 有效(x.get(k),n): fail.append(f"内容章节{i}缺少有效字段：{k}")
    if got!=章节: fail.append("内容五章未完整覆盖：看见、认出、相信、参与、见证")

    touch=列表(d.get("触点一致性"))
    if len(touch)<5: fail.append("触点一致性少于5项")
    verify=列表(d.get("验证计划"))
    if len(verify)<4: fail.append("验证计划少于4项，无法判断传播是否改变信念与行动")

    print(f"人文传播关：{len(aud)}类受众；{len(got)}章内容；{len(touch)}个触点")
    if fail:
        print("\n不通过：")
        for x in dict.fromkeys(fail): print("- "+x)
        return 1
    print("\n通过：人文概念已翻译为分众信念、证据、内容与行动链。")
    return 0

if __name__=="__main__": sys.exit(main())

