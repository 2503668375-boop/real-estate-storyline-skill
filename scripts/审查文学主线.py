#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审查逻辑与情绪文学是否逐步汇聚到概念，并校验可选多语命名底稿。"""
import argparse, json, re, sys
from pathlib import Path

节点={"事实资产","机制解释","人物任务","竞争旧答案","关键矛盾","价值机会","战略取舍","总价值主张","证明机制","经营后果"}
语言={"中文","英文","法文","西班牙文","意大利文","德文","日文","其他"}
空词={"美好生活","高端生活","世界审美","时代封面","城市作品","定义未来","塔尖圈层"}

def 文本(v): return re.sub(r"\s+","",str(v or "")).strip()
def 有效(v,n=6): return len(文本(v))>=n and 文本(v) not in 空词
def 列表(v): return v if isinstance(v,list) else []

def 自测数据():
    chain=[]
    for i,node in enumerate(list(节点)[:8],1):
        chain.append({"逻辑节点":node,"事实判断":f"第{i}项事实说明项目机制如何改变家庭的真实生活",
            "客户痛点":f"客户在第{i}个具体生活场景中持续承担时间关系与选择代价",
            "价值回应":f"项目以第{i}项空间产品或服务机制回应并减少这项代价",
            "文学标题":f"第{i}次转折，让被忽略的生活重新被看见",
            "人物动作":f"一家人在普通一天完成第{i}个可被拍摄和观察的动作",
            "意象来源":"来自现场动线、地方生活和人物真实动作",
            "承上句":"上一项事实让这项人物代价不再只是偶然",
            "启下句":"因此下一步必须从资源判断进入价值选择"})
    names=[
        {"语言":"英文","原文":"Common Ground","发音":"康门格朗德","字面义":"共同的土地与共同基础",
         "文化语境":"强调共享基础和关系建立","对应中文内核":"各自自在仍然相连的共同生活",
         "为何使用该语言":"现代都会语感与项目建筑表达一致","声音与调性":"简短克制便于传播",
         "文化风险":"可能偏公共空间概念需避免泛化","核验状态":"待母语商标重名核验"},
        {"语言":"法文","原文":"Lien","发音":"利安","字面义":"联系与纽带",
         "文化语境":"表达人与人之间的关系连接","对应中文内核":"尊重边界但保持回应",
         "为何使用该语言":"适配克制的人文艺术调性","声音与调性":"单词简洁有轻盈节奏",
         "文化风险":"需核验法语发音和既有品牌","核验状态":"待母语商标重名核验"},
        {"语言":"西班牙文","原文":"Cerca","发音":"塞尔卡","字面义":"靠近与附近",
         "文化语境":"强调人与日常生活的接近","对应中文内核":"让共同生活自然发生",
         "为何使用该语言":"适配温暖开放的家庭生活气质","声音与调性":"有温度且容易记忆",
         "文化风险":"可能与通用词和既有项目重名","核验状态":"待母语商标重名核验"}]
    return {"情绪母线":{"目标人物":"承担时间和关系压力的双职工改善家庭","初始情绪":"拥有更多选择却越来越难真正相处",
            "隐性痛点":[f"第{i}项可观察的时间关系或身份代价" for i in range(1,6)],
            "核心欲望":[f"第{i}项关于自由亲密边界成长或归属的欲望" for i in range(1,6)],
            "情绪转折":"项目说破问题并以真实机制让共同生活不再需要反复组织",
            "终局感受":"每个人保有自己的节奏仍能确认彼此就在身边"},
        "逻辑文学链":chain,
        "概念集中":{"核心矛盾":"家庭想保持亲密又不愿以牺牲个人边界为代价","价值选择":"让不同节奏保持可见可达和可回应",
            "概念命题":"共同生活不必要求所有人时刻做同一件事","中文主张":"各自自在，仍然相连",
            "概念长文":"真正的共同生活，并不是把一家人安排进同一张日程表。它允许老人安静休息，孩子自在生长，父母保有自己的工作与兴趣；也让每个人抬头时，知道彼此仍在可以回应的距离里。项目以连续动线、并行空间与持续运营，把这种不必勉强同步的亲密，变成每天自然发生的生活。",
            "30秒讲法":"因为项目让家庭成员可以各做各事又彼此看见，所以换房得到的不只是更多空间，而是一种不必互相牺牲的共同生活。",
            "最后一跳":"当所有空间都在保护边界同时创造回应，项目最终集中为各自自在仍然相连。"},
        "国内表达审校":[{"原句":"定义塔尖圈层的世界生活","风险":"宏大空泛且没有人物","改写":"让一家人不必互相退让也能彼此照应"} for _ in range(5)],
        "是否需要多语命名":True,"多语命名候选":names,
        "多语最终选择":{"候选原文":"Common Ground","选择理由":"语义与共同生活机制一致且声音克制",
            "与中文案名关系":"外语名负责现代调性中文主张负责思想解释","核验状态":"方向待核验"}}

def 审查(d):
    fail=[]
    mood=d.get("情绪母线",{}) if isinstance(d.get("情绪母线"),dict) else {}
    for k,n in (("目标人物",8),("初始情绪",10),("情绪转折",12),("终局感受",10)):
        if not 有效(mood.get(k),n): fail.append("情绪母线缺少有效字段："+k)
    pains=列表(mood.get("隐性痛点")); desires=列表(mood.get("核心欲望"))
    if len(pains)<5: fail.append(f"隐性痛点少于5项（实际{len(pains)}）")
    if len(desires)<5: fail.append(f"核心欲望少于5项（实际{len(desires)}）")

    chain=列表(d.get("逻辑文学链")); covered=set(); titles=[]
    if len(chain)<8: fail.append(f"逻辑文学链少于8个节点（实际{len(chain)}）")
    for i,x in enumerate(chain,1):
        if not isinstance(x,dict): fail.append(f"文学节点{i}不是结构化卡片"); continue
        node=文本(x.get("逻辑节点")); covered.add(node)
        if node not in 节点: fail.append(f"文学节点{i}逻辑节点无效")
        for k,n in (("事实判断",10),("客户痛点",10),("价值回应",10),("文学标题",8),("人物动作",8),("意象来源",8),("承上句",8),("启下句",8)):
            if not 有效(x.get(k),n): fail.append(f"文学节点{i}缺少有效字段：{k}")
        titles.append(文本(x.get("文学标题")))
    if len(covered & 节点)<8: fail.append(f"逻辑文学链覆盖的不同推导任务少于8个（实际{len(covered & 节点)}）")
    if len(titles)!=len(set(titles)): fail.append("文学标题存在重复，未形成情绪递进")

    focus=d.get("概念集中",{}) if isinstance(d.get("概念集中"),dict) else {}
    for k,n in (("核心矛盾",12),("价值选择",10),("概念命题",12),("中文主张",4),("概念长文",100),("30秒讲法",30),("最后一跳",20)):
        if not 有效(focus.get(k),n): fail.append("概念集中缺少有效字段："+k)

    edits=列表(d.get("国内表达审校"))
    if len(edits)<5: fail.append("国内表达审校少于5项")
    for i,x in enumerate(edits,1):
        if not isinstance(x,dict) or any(not 有效(x.get(k),4) for k in ("原句","风险","改写")):
            fail.append(f"国内表达审校{i}字段不全")

    names=列表(d.get("多语命名候选"))
    if d.get("是否需要多语命名") is True:
        if len(names)<3: fail.append(f"多语命名候选少于3个（实际{len(names)}）")
        for i,x in enumerate(names,1):
            if not isinstance(x,dict): fail.append(f"多语候选{i}不是结构化卡片"); continue
            if 文本(x.get("语言")) not in 语言-{"中文"}: fail.append(f"多语候选{i}语言无效")
            for k,n in (("原文",3),("发音",2),("字面义",4),("文化语境",6),("对应中文内核",8),("为何使用该语言",8),("声音与调性",6),("文化风险",6),("核验状态",4)):
                if not 有效(x.get(k),n): fail.append(f"多语候选{i}缺少有效字段：{k}")
        final=d.get("多语最终选择",{}) if isinstance(d.get("多语最终选择"),dict) else {}
        for k,n in (("候选原文",3),("选择理由",8),("与中文案名关系",8),("核验状态",4)):
            if not 有效(final.get(k),n): fail.append("多语最终选择缺少有效字段："+k)
    return fail,(len(pains),len(chain),len(covered & 节点),len(edits),len(names))

def main():
    p=argparse.ArgumentParser(); p.add_argument("底稿",type=Path,nargs="?"); p.add_argument("--自检",action="store_true"); a=p.parse_args()
    if a.自检:d=自测数据()
    elif a.底稿:
        try:d=json.loads(a.底稿.read_text(encoding="utf-8"))
        except Exception as e: print("文学主线关：无法读取：",e); return 2
    else:p.error("必须提供底稿或使用 --自检")
    fail,c=审查(d)
    print(f"文学主线关：痛点{c[0]}；链条{c[1]}节点/{c[2]}任务；国内审校{c[3]}；多语候选{c[4]}")
    if fail:
        print("\n不通过：")
        for x in dict.fromkeys(fail): print("- "+x)
        return 1
    print("\n通过：逻辑、情绪与文学逐步汇聚到概念；多语命名仍须母语、商标和重名核验。")
    return 0

if __name__=="__main__": sys.exit(main())

