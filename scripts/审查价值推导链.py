#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拦截只有价值结论、没有推导过程与证明机制的底稿。"""
import argparse, json, re, sys
from pathlib import Path

根=Path(__file__).resolve().parents[1]
规则=json.loads((根/"references"/"统一规则.json").read_text(encoding="utf-8"))
占位={"","待定","待核实","TBD","-","—","高端","品质","美好","稀缺","唯一"}
任务=set(规则["价值推导任务"])

def 文本(v): return re.sub(r"\s+","",str(v or "")).strip()
def 有效(v,n=6): return len(文本(v))>=n and 文本(v) not in 占位
def 列表(v): return v if isinstance(v,list) else []

def main():
    p=argparse.ArgumentParser()
    p.add_argument("底稿",type=Path)
    p.add_argument("--类型",choices=["完整","核心","摘要"],default="完整")
    a=p.parse_args()
    try:d=json.loads(a.底稿.read_text(encoding="utf-8"))
    except Exception as e: print("价值推导关：无法读取：",e); return 2
    fail=[]
    if d.get("资料等级")!="A": fail.append("资料等级必须为A；B/C级只能形成待验证方向")

    chain=d.get("推导链",{}) if isinstance(d.get("推导链"),dict) else {}
    for k in 任务:
        if not 有效(chain.get(k),10): fail.append("推导链缺少有效阶段："+k)

    pillars=列表(d.get("价值支柱"))
    if len(pillars)<3: fail.append(f"价值支柱少于3个（实际{len(pillars)}）")
    必填=(("名称",3),("客户任务",8),("痛点或代价",8),("项目机制",10),("客户可感知结果",8),
          ("可指认证据",8),("竞品结构差异",8),("支付或选择理由",8),("失败边界",6))
    for i,x in enumerate(pillars,1):
        if not isinstance(x,dict): fail.append(f"价值支柱{i}不是结构化卡片"); continue
        for k,n in 必填:
            if not 有效(x.get(k),n): fail.append(f"价值支柱{i}缺少有效字段：{k}")
        acts=列表(x.get("产品空间服务动作"))
        if len(acts)<2 or any(not 有效(v,6) for v in acts):
            fail.append(f"价值支柱{i}至少需要2项具体产品/空间/服务动作")

    opportunities=列表(d.get("价值矛盾地图"))
    if len(opportunities)<3:
        fail.append(f"价值矛盾地图少于3个机会（实际{len(opportunities)}）")
    for i,x in enumerate(opportunities,1):
        if not isinstance(x,dict): fail.append(f"价值机会{i}不是结构化卡片"); continue
        for k,n in (("机会",4),("放大事实",8),("人物代价",8),("项目机制",8),("获得",8),("牺牲",8),("竞品可复制性",8),("停止条件",8)):
            if not 有效(x.get(k),n): fail.append(f"价值机会{i}缺少有效字段：{k}")
    if opportunities and sum(1 for x in opportunities if isinstance(x,dict) and x.get("唯一推荐") is True)!=1:
        fail.append("价值矛盾地图必须恰有一个唯一推荐")

    links=列表(d.get("六联单"))
    if len(links)<len(pillars):
        fail.append(f"六联单少于价值支柱数量（六联单{len(links)}，支柱{len(pillars)}）")
    for i,x in enumerate(links,1):
        if not isinstance(x,dict): fail.append(f"六联单{i}不是结构化卡片"); continue
        for k,n in (("人物任务",8),("项目机制",8),("产品空间参数",8),("展示证据",8),("销售讲法",8),("阶段营销动作",8)):
            if not 有效(x.get(k),n): fail.append(f"六联单{i}缺少有效字段：{k}")

    pages=列表(d.get("推导页面"))
    min_pages=规则["价值推导页数"][a.类型][0]
    if len(pages)<min_pages: fail.append(f"{a.类型}稿价值推导页面少于{min_pages}页（实际{len(pages)}）")
    covered=set()
    for i,x in enumerate(pages,1):
        if not isinstance(x,dict): fail.append(f"推导页面{i}不是结构化卡片"); continue
        raw_tasks=x.get("推导任务")
        page_tasks=raw_tasks if isinstance(raw_tasks,list) else [raw_tasks]
        valid_tasks={文本(v) for v in page_tasks if 文本(v) in 任务}
        invalid_tasks=[文本(v) for v in page_tasks if 文本(v) and 文本(v) not in 任务]
        if not valid_tasks: fail.append(f"推导页面{i}未填写有效推导任务")
        if invalid_tasks: fail.append(f"推导页面{i}的推导任务无效：{'、'.join(invalid_tasks)}")
        covered.update(valid_tasks)
        for k,n in (("页面任务",6),("上游输入",8),("新判断",10),("证据",8),("排除的旧选项",8),("下游决定",8),("情绪任务",6),("人物动作",6),("承上句",8),("启下句",8)):
            if not 有效(x.get(k),n): fail.append(f"推导页面{i}缺少有效字段：{k}")
    min_tasks={"完整":len(任务),"核心":8,"摘要":2}[a.类型]
    if len(covered)<min_tasks: fail.append(f"{a.类型}稿覆盖的不同推导任务少于{min_tasks}个（实际{len(covered)}）")

    emotion_cards=列表(d.get("章节情绪卡"))
    min_emotions={"完整":5,"核心":3,"摘要":1}[a.类型]
    if len(emotion_cards)<min_emotions:
        fail.append(f"{a.类型}稿章节情绪卡少于{min_emotions}张（实际{len(emotion_cards)}）")
    for i,x in enumerate(emotion_cards,1):
        if not isinstance(x,dict): fail.append(f"章节情绪卡{i}不是结构化卡片"); continue
        for k,n in (("入章情绪",4),("张力",6),("转折事实或场景",8),("离章情绪",4),("下章疑问",8)):
            if not 有效(x.get(k),n): fail.append(f"章节情绪卡{i}缺少有效字段：{k}")

    scenes=列表(d.get("场景单元"))
    min_scenes={"完整":3,"核心":2,"摘要":1}[a.类型]
    if len(scenes)<min_scenes:
        fail.append(f"{a.类型}稿场景单元少于{min_scenes}个（实际{len(scenes)}）")
    for i,x in enumerate(scenes,1):
        if not isinstance(x,dict): fail.append(f"场景单元{i}不是结构化卡片"); continue
        for k,n in (("人物",3),("时刻",3),("动作",6),("物件或感官",4),("阻碍",6),("代价",6),("项目机制",8),("改变",8),("验证",6)):
            if not 有效(x.get(k),n): fail.append(f"场景单元{i}缺少有效字段：{k}")

    imagery=d.get("意象系统",{}) if isinstance(d.get("意象系统"),dict) else {}
    for k,n in (("主意象",3),("辅助意象",4),("事实来源",8),("四次递进",12),("禁用边界",8)):
        if not 有效(imagery.get(k),n): fail.append("意象系统缺少："+k)

    checks=d.get("反向校验",{}) if isinstance(d.get("反向校验"),dict) else {}
    for k in ("换盘","资料不足时如何收缩结论","删页测试","价格测试","销售复述"):
        if not 有效(checks.get(k),8): fail.append("反向校验缺少："+k)

    print(f"价值推导关：{len(pages)}页；{len(covered)}类推导任务；{len(emotion_cards)}张情绪卡；{len(scenes)}个场景单元；{len(pillars)}个价值支柱；{len(opportunities)}个价值机会；{len(links)}张六联单")
    if fail:
        print("\n不通过：")
        for x in dict.fromkeys(fail): print("- "+x)
        return 1
    print("\n通过：价值结论已有完整上游因果、证明机制与下游经营责任。")
    return 0

if __name__=="__main__": sys.exit(main())
