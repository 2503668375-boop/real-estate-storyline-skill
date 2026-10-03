#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审查7.4故事线在进入经营与页面编排前是否真正成立。"""
import argparse, json, re, sys
from pathlib import Path

占位 = {"", "待定", "待核实", "TBD", "-", "—", "A", "B", "C", "测试", "示例"}
泛母题 = {"美好生活", "理想生活", "向往生活", "从容生活", "松弛生活", "时代作品", "城市封面", "未来生活"}

def 文本(v): return re.sub(r"\s+", "", v.strip()) if isinstance(v, str) else ""
def 有意义(v, 最短=4):
    s=文本(v)
    return len(s)>=最短 and s not in 占位 and not re.fullmatch(r"[A-Za-z0-9_-]{1,3}",s)
def 检查卡片(列表, 最少, 字段, 名称, 失败):
    if not isinstance(列表,list) or len(列表)<最少:
        失败.append(f"{名称}少于{最少}项"); return []
    for i,x in enumerate(列表,1):
        if not isinstance(x,dict): 失败.append(f"{名称}{i}不是结构化卡片"); continue
        for k,n in 字段:
            if not 有意义(x.get(k),n): 失败.append(f"{名称}{i}缺少有效字段：{k}")
    return 列表

def main():
    p=argparse.ArgumentParser(); p.add_argument("底稿",type=Path); p.add_argument("--有标杆",action="store_true"); p.add_argument("--要求精神引文",action="store_true"); a=p.parse_args()
    try: d=json.loads(a.底稿.read_text(encoding="utf-8"))
    except Exception as e: print("故事线审查关：无法读取底稿：",e); return 2
    失败=[]

    前置=d.get("前置审查",{})
    if 前置.get("资料等级") != "A": 失败.append("前置审查资料等级必须为A")
    if 前置.get("概念比选审查") != "通过": 失败.append("缺少概念比选通过结论")
    if not 有意义(前置.get("概念比选底稿路径"),6): 失败.append("前置审查缺少概念比选底稿路径")
    if 前置.get("创意总监审查") != "通过": 失败.append("缺少三重隔离创意总监审查通过结论")
    if not 有意义(前置.get("创意底稿路径"),6): 失败.append("前置审查缺少创意底稿路径")
    if 前置.get("价值推导审查") != "通过": 失败.append("缺少价值推导审查通过结论")
    if not 有意义(前置.get("价值推导底稿路径"),6): 失败.append("前置审查缺少价值推导底稿路径")
    if 前置.get("文学主线审查") != "通过": 失败.append("缺少文学主线审查通过结论")
    if not 有意义(前置.get("文学主线底稿路径"),6): 失败.append("前置审查缺少文学主线底稿路径")
    if 前置.get("人文传播审查") != "通过": 失败.append("缺少人文传播审查通过结论")
    if not 有意义(前置.get("人文传播底稿路径"),6): 失败.append("前置审查缺少人文传播底稿路径")

    if a.有标杆:
        r=d.get("参考标杆",{})
        for k,n in (("文件",5),("页数",1)):
            if not (有意义(r.get(k),n) or (k=="页数" and isinstance(r.get(k),int) and r[k]>0)): 失败.append("参考标杆缺少："+k)
        if not isinstance(r.get("方法骨架"),list) or len(r["方法骨架"])<5: 失败.append("参考标杆方法骨架少于5项")
        if not isinstance(r.get("本项目不可复制内容"),list) or len(r["本项目不可复制内容"])<3: 失败.append("参考标杆未写至少3项不可复制内容")

    land=d.get("土地叙事",{})
    检查卡片(land.get("不可替代事实"),5,(("事实",8),("来源",4),("时间",4),("影响",10)),"土地事实",失败)
    if not 有意义(land.get("真实矛盾"),20): 失败.append("土地叙事缺少具体真实矛盾")
    演变=land.get("土地演变")
    if not ((isinstance(演变,list) and len(演变)>=2 and all(有意义(x,6) for x in 演变)) or 有意义(演变,24)): 失败.append("土地演变缺少至少2个阶段或完整叙述")

    people=d.get("人物精神处境",{})
    检查卡片(people.get("人物处境卡"),3,(("人群",4),("生活冲突",12),("精神渴望",8),("拒绝什么",8),("对空间的要求",10)),"人物处境卡",失败)

    core=d.get("精神母题",{})
    dirs=检查卡片(core.get("初步方向"),60,(("方向",3),("概念切入角度",3),("事实支点",12),("人物共鸣",12),("空间后果",10)),"初步方向",失败)
    名称=[文本(x.get("方向")) for x in dirs if isinstance(x,dict)]
    if len(名称)!=len(set(名称)): 失败.append("精神方向存在换词重复或同名")
    finals=core.get("重点方向")
    if not isinstance(finals,list) or len(finals)!=4: 失败.append("精神母题重点方向必须恰为4项")
    else: 检查卡片(finals,4,(("名称",3),("反命题",8),("空间原型候选",6),("选择或排除理由",10)),"重点方向",失败)
    for k,n in (("主命题",4),("项目反命题",12),("精神来源",16)):
        if not 有意义(core.get(k),n): 失败.append("精神母题缺少有效字段："+k)
    if 文本(core.get("主命题")) in 泛母题: 失败.append("主命题为可替换泛词，必须从项目事实重做")

    director=d.get("叙事导演卡",{})
    for k,n in (("主切入角度",3),("辅助切入角度",3),("选择依据",16),("事实锚点",16),("禁用联想",6),("叙事对象",4),("失效或撤回条件",10)):
        if not 有意义(director.get(k),n): 失败.append("叙事导演卡缺少有效字段："+k)
    allowed={"城市价值","历史文脉","生活方式","价值观共鸣","城市事件","IP或符号"}
    if 文本(director.get("主切入角度")) not in allowed: 失败.append("叙事导演卡主切入角度不在允许分类中")
    if 文本(director.get("主切入角度")) in 文本(director.get("辅助切入角度")): 失败.append("叙事导演卡主辅角度重复")
    rhythm=d.get("情感节奏卡",{})
    for k,n in (("进入",6),("触动",6),("共鸣",6),("认同",6),("余韵",6),("高点位置",4)):
        if not 有意义(rhythm.get(k),n): 失败.append("情感节奏卡缺少有效字段："+k)
    anchors=rhythm.get("情感锚点")
    检查卡片(anchors,2,(("类型",2),("人物或细节",8),("事实或机制",8),("所在章节",3)),"情感锚点",失败)
    symbols=d.get("视觉母题卡")
    检查卡片(symbols,1,(("母题",2),("事实来源",8),("人物或生活连接",8),("视觉语言",8),("空间或传播触点",8),("禁用俗套",4)),"视觉母题卡",失败)
    for x in symbols if isinstance(symbols,list) else []:
        if isinstance(x,dict) and 文本(x.get("母题")) in {"光","水","山","自然","未来","梦想"}: 失败.append("视觉母题卡使用泛化母题，必须具体化")

    spatial=d.get("空间原型",{})
    for k,n in (("名称",4),("结构说明",16),("连接机制",12),("不可替代性",12)):
        if not 有意义(spatial.get(k),n): 失败.append("空间原型缺少有效字段："+k)
    检查卡片(spatial.get("空间组件"),3,(("名称",3),("位置",4),("连接",6),("日常使用",8),("溢价机制",8)),"空间组件",失败)

    ips=检查卡片(d.get("价值IP与场景"),3,(("名称",3),("位置",4),("使用者",4),("使用频率",3),("空间或运营动作",10),("客户价值",8),("项目价值",8)),"价值IP",失败)
    ip名=[文本(x.get("名称")) for x in ips if isinstance(x,dict)]
    if len(ip名)!=len(set(ip名)): 失败.append("价值IP存在同名重复")

    maps=d.get("价值兑现",{})
    for branch in ("产品","价格","营销"):
        检查卡片(maps.get(branch),3,(("母题或原型",3),("动作",8),("证据",8)),f"价值兑现-{branch}",失败)

    chain=d.get("标题链")
    rows=检查卡片(chain,12,(("标题",6),("页面任务",2),("新增内容",8),("视觉证据",5),("决策后果",8),("删除测试",6)),"标题链",失败)
    if isinstance(chain,list) and len(chain)>18: 失败.append("标题链超过18页，应先合并")
    标题=[文本(x.get("标题")) for x in rows if isinstance(x,dict)]
    if len(标题)!=len(set(标题)): 失败.append("标题链存在重复标题")
    全链=" ".join(标题+[文本(x.get("页面任务")) for x in rows if isinstance(x,dict)])
    for 段,模式 in (("土地",r"土地|地块|前史|地理"),("人物",r"人物|人群|客户|家庭"),("精神",r"精神|母题|主张|相信"),("空间原型",r"空间|原型|结构|总图"),("IP场景",r"IP|场景|日常|运营"),("支付理由",r"支付|价格|溢价|值得")):
        if not re.search(模式,全链,re.I): 失败.append("标题链未覆盖："+段)
    if sum(bool(re.search(r"首开前|首开后|首开当周|每次加推",x)) for x in 标题)>3: 失败.append("标题链被营销时间窗主导，最多允许3页")

    quotes=d.get("署名引文",[])
    if not isinstance(quotes,list) or len(quotes)>3: 失败.append("署名引文必须为0—3条")
    if a.要求精神引文 and (not isinstance(quotes,list) or len(quotes)<1): 失败.append("已要求精神引文，但没有形成至少1条引文价值链")
    for i,q in enumerate(quotes if isinstance(quotes,list) else [],1):
        if not isinstance(q,dict): 失败.append(f"署名引文{i}不是结构化卡片"); continue
        for k,n in (("原文",4),("作者",2),("原文出处",6),("核验日期",8),("项目组译",4),("它打开的价值判断",10),("它改变的空间或产品决定",10)):
            if not 有意义(q.get(k),n): 失败.append(f"署名引文{i}缺少有效字段：{k}")

    if 失败:
        print("故事线审查关：未通过"); [print("- "+x) for x in dict.fromkeys(失败)]; return 1
    print("故事线审查关：通过；允许进入经营校验与主方案编排。\n")
    print("主命题："+core["主命题"]+"\n空间原型："+spatial["名称"]+"\nIP数量："+str(len(ips))+"\n标题链："+str(len(rows))+"页")
    return 0
if __name__=="__main__": sys.exit(main())
