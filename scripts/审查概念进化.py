#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审查概念是否经过足量异质发散、变异和对抗，而非从首个灵感直接命名。"""
import argparse, json, re, sys
from collections import Counter
from pathlib import Path

角度=["反常识翻转","矛盾加压","取舍显影","身份重命名","关系重构","时间改写",
    "空间做法","城市角色","地方文化","自然条件","品牌能力","跳出行业常规"]
角色=["创意总监","竞品偷窃者","客户怀疑者","产品工程师","文化批评者","经营负责人"]
变异={"反转","加压","具身","换尺度","机制化","去修辞","商业化","文化化"}

def 文本(v): return re.sub(r"\s+","",str(v or "")).strip()
def 有效(v,n=6): return len(文本(v))>=n and 文本(v) not in {"待定","待核实","TBD","-","—"}
def 列表(v): return v if isinstance(v,list) else []

def 构造自测():
    evidence=[{"ID":f"E{i:02d}","事实":f"第{i}条经来源核验的项目事实会改变具体产品与经营判断","来源":"规划文件与现场核验","置信度":"高","改变什么":"改变空间与价值解释"} for i in range(1,21)]
    tensions=[{"ID":f"T{i:02d}","谁":"具体家庭决策者","想得到什么":"获得更丰富且可持续的共同生活","害怕失去什么":"失去个人边界与家庭时间","行为证据":"用接送比较拒绝和支付行为证明","项目能否介入":"可通过真实空间运营做法介入"} for i in range(1,9)]
    cliches=[{"套话":f"行业陈词{i}","竞品":"直接竞品","证明方式":"效果图与通用配置","为何失效":"无法形成项目独有因果"} for i in range(1,13)]
    seeds=[]
    for idx,angle in enumerate(角度):
        for j in range(5):
            n=idx*5+j+1
            seeds.append({"ID":f"S{n:02d}","概念切入角度":angle,"项目事实ID":[f"E{(n%20)+1:02d}",f"E{((n+6)%20)+1:02d}"],
                "客户矛盾ID":f"T{(n%8)+1:02d}","核心判断":f"初步方向{n}重新解释项目与人物关系",
                "反对什么":"反对行业用配置数量替代真实生活结果","意外新理解":"项目价值来自可重复机制而非资源罗列",
                "人物场景":"一家人在普通工作日晚间完成真实选择","情绪触发":"让客户认出长期被忽略的时间与关系代价",
                "兑现做法":"由总图产品服务和运营共同兑现",
                "改变什么":"改变产品取舍价格解释展示顺序和传播内容"})
    evolved=[]
    for i in range(1,19):
        evolved.append({"ID":f"M{i:02d}","来源种子ID":[f"S{i:02d}",f"S{i+18:02d}"],"变异方式":["具身","机制化"],
            "核心判断":f"深化方向{i}提出明确且可占有的新价值判断","新理解":"把人物代价重新解释为项目必须解决的核心问题",
            "项目专属因果":"两条项目事实与一个人物矛盾共同导出且换给竞品不能成立",
            "人物场景":"客户在具体家庭讨论中因证据改变选择","情绪核心":"既想保有自己又不愿失去彼此",
            "文学命题":"真正的共同生活不要求所有人时刻做同一件事",
            "带出的产品经营动作":[f"改变产品经营决策{k}" for k in range(1,6)],
            "带出的表达与传播":["总主张系统","空间命名系统","连续内容计划"],
            "失败边界":"关键图纸或客户证据不成立时淘汰"})
    finalists=[]
    reviews=[]
    for i in range(1,5):
        finalists.append({"ID":f"F{i}","来源深化方向ID":f"M{i:02d}","核心判断":f"重点方向{i}形成排他的思想资产",
            "核心取舍":"选择高频真实生活并放弃低频炫耀配置","第二选择差异":"与另一方向在人物和机制因果上明确不同",
            "不成立条件":"客户行为或空间做法证据不成立时推翻","带出的后续工作":"可生成价值空间人文命名和阶段营销系统",
            "文学集中句":"各自自在仍然相连让全部人物情绪集中到一个生活选择"})
        for role in 角色:
            reviews.append({"概念ID":f"F{i}","角色":role,"最强攻击":"指出概念最可能被偷窃不信或无法兑现的断点",
                "暴露断点":"某项证据与产品机制之间仍需进一步核验",
                "修复后概念":"保留核心取舍并补充可指认机制与边界",
                "结论":"保留"})
    return {"项目事实":evidence,"客户矛盾":tensions,"市场套话":cliches,"初步方向":seeds,
            "深化方向":evolved,"重点方向":finalists,"反向挑刺":reviews,
            "最终选择":{"胜出概念ID":"F1","押注理由":"它最能改变市场原有理解并拥有项目独有证据",
                "主动舍弃":"放弃追求全客群和所有审美同时满意","第二名未选原因":"第二名更安全但缺少认知位移",
                "可证伪条件":"关键客户行为与空间机制被新证据否定",
                "下游生成":"生成价值体系空间概念人文传播案名和连续战役"}}

def 审查(d):
    fail=[]
    evidence=列表(d.get("项目事实")); tensions=列表(d.get("客户矛盾")); cliches=列表(d.get("市场套话"))
    if len(evidence)<20: fail.append(f"项目事实少于20条（实际{len(evidence)}）")
    if len(tensions)<8: fail.append(f"客户矛盾少于8条（实际{len(tensions)}）")
    if len(cliches)<12: fail.append(f"市场套话少于12条（实际{len(cliches)}）")
    eids={文本(x.get("ID")) for x in evidence if isinstance(x,dict)}
    tids={文本(x.get("ID")) for x in tensions if isinstance(x,dict)}

    seeds=列表(d.get("初步方向")); counts=Counter()
    if len(seeds)<60: fail.append(f"初步方向少于60个（实际{len(seeds)}）")
    for i,x in enumerate(seeds,1):
        if not isinstance(x,dict): fail.append(f"种子{i}不是结构化卡片"); continue
        angle=文本(x.get("概念切入角度")); counts[angle]+=1
        if angle not in 角度: fail.append(f"初步方向{i}的概念切入角度无效")
        refs=列表(x.get("项目事实ID"))
        if len(set(map(文本,refs)))<2 or any(文本(v) not in eids for v in refs):
            fail.append(f"初步方向{i}未引用2个有效项目事实")
        if 文本(x.get("客户矛盾ID")) not in tids: fail.append(f"初步方向{i}未引用有效客户矛盾")
        for k,n in (("核心判断",8),("反对什么",8),("意外新理解",8),("人物场景",8),("情绪触发",8),("兑现做法",8),("改变什么",8)):
            if not 有效(x.get(k),n): fail.append(f"初步方向{i}缺少有效字段：{k}")
    for angle in 角度:
        if counts[angle]<5: fail.append(f"概念切入角度“{angle}”少于5个初步方向（实际{counts[angle]}）")

    evolved=列表(d.get("深化方向"))
    if len(evolved)<18: fail.append(f"深化方向少于18个（实际{len(evolved)}）")
    mids=set()
    for i,x in enumerate(evolved,1):
        if not isinstance(x,dict): fail.append(f"深化方向{i}不是结构化卡片"); continue
        mids.add(文本(x.get("ID")))
        methods=set(map(文本,列表(x.get("变异方式"))))
        if len(methods & 变异)<2: fail.append(f"深化方向{i}少于2种有效变异")
        for k,n in (("核心判断",10),("新理解",10),("项目专属因果",12),("人物场景",8),("情绪核心",8),("文学命题",10),("失败边界",8)):
            if not 有效(x.get(k),n): fail.append(f"深化方向{i}缺少有效字段：{k}")
        if len(列表(x.get("带出的产品经营动作")))<5: fail.append(f"深化方向{i}与已定产品经营结论的映射少于5项")
        if len(列表(x.get("带出的表达与传播")))<3: fail.append(f"深化方向{i}带出的表达与传播少于3项")

    finals=列表(d.get("重点方向")); fids=set()
    if len(finals)!=4: fail.append(f"重点方向必须恰为4个（实际{len(finals)}）")
    for i,x in enumerate(finals,1):
        if not isinstance(x,dict): fail.append(f"重点方向{i}不是结构化卡片"); continue
        fids.add(文本(x.get("ID")))
        if 文本(x.get("来源深化方向ID")) not in mids: fail.append(f"重点方向{i}未引用有效深化方向")
        for k,n in (("核心判断",10),("核心取舍",10),("第二选择差异",10),("不成立条件",10),("带出的后续工作",10),("文学集中句",10)):
            if not 有效(x.get(k),n): fail.append(f"重点方向{i}缺少有效字段：{k}")

    reviews=列表(d.get("反向挑刺")); pairs=set()
    if len(reviews)<24: fail.append(f"反向挑刺少于24张（实际{len(reviews)}）")
    for i,x in enumerate(reviews,1):
        if not isinstance(x,dict): fail.append(f"反向挑刺{i}不是结构化卡片"); continue
        fid,role=文本(x.get("概念ID")),文本(x.get("角色")); pairs.add((fid,role))
        if fid not in fids or role not in 角色: fail.append(f"反向挑刺{i}概念或角色无效")
        for k,n in (("最强攻击",10),("暴露断点",10),("修复后概念",10),("结论",2)):
            if not 有效(x.get(k),n): fail.append(f"反向挑刺{i}缺少有效字段：{k}")
    for fid in fids:
        for role in 角色:
            if (fid,role) not in pairs: fail.append(f"{fid}缺少{role}反向挑刺")

    choice=d.get("最终选择",{}) if isinstance(d.get("最终选择"),dict) else {}
    if 文本(choice.get("胜出概念ID")) not in fids: fail.append("最终选择未引用重点方向")
    for k,n in (("押注理由",12),("主动舍弃",10),("第二名未选原因",10),("可证伪条件",10),("下游生成",10)):
        if not 有效(choice.get(k),n): fail.append("最终选择缺少有效字段："+k)
    return fail,(len(evidence),len(tensions),len(seeds),len(evolved),len(finals),len(reviews))

def main():
    p=argparse.ArgumentParser(); p.add_argument("底稿",type=Path,nargs="?"); p.add_argument("--自检",action="store_true"); a=p.parse_args()
    if a.自检: d=构造自测()
    elif a.底稿:
        try:d=json.loads(a.底稿.read_text(encoding="utf-8"))
        except Exception as e: print("概念比选审查：无法读取：",e); return 2
    else: p.error("必须提供底稿或使用 --自检")
    fail,counts=审查(d)
    print(f"概念比选审查：项目事实{counts[0]}；客户矛盾{counts[1]}；初步方向{counts[2]}；深化方向{counts[3]}；重点方向{counts[4]}；反向挑刺{counts[5]}")
    if fail:
        print("\n不通过：")
        for x in dict.fromkeys(fail): print("- "+x)
        return 1
    print("\n通过：概念完成足量异质发散、两轮深化与六角色反向挑刺；创意质量仍须独立审美判断。")
    return 0

if __name__=="__main__": sys.exit(main())
