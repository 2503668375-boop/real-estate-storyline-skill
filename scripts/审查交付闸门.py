#!/usr/bin/env python3
"""审查8.1内部经营底稿：产品结构、成本、利润、现金流、价格与首开。"""
import argparse, json, sys
from pathlib import Path

必需顶层 = {
    "决策定义": ["项目阶段", "需批准事项", "联网状态"],
    "事实与竞争": ["项目事实", "竞品价格口径", "来源表"],
    "经营价格": ["可售面积", "土地分摊", "建安", "精装", "财务", "税费", "营销", "总成本", "单位成本", "不含利润盈亏平衡", "现金流安全售价", "目标利润", "目标利润售价", "市场可实现价", "客户支付上限", "推荐首开成交价", "预计收入", "毛利额", "毛利率", "现金流峰值", "回正时间", "敏感性"],
    "客户资金": ["客户卡"],
    "精神内核": ["概念进化结论", "四强差异", "最终主命题", "母题资格审查"],
    "产品预判营销": ["产品结构比较", "产品结构", "客群空间任务", "三情境", "首开战役", "开盘日运行"],
}
客户字段 = ["现居与持有资产", "可出售资产", "可调现金", "首付/全款/融资方式", "流动性保留", "可承受总价", "比较项目", "触发事件", "第一否决点", "成交证据"]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("底稿",type=Path); ap.add_argument("--类型",default="完整")
    a=ap.parse_args()
    try: d=json.loads(a.底稿.read_text(encoding="utf-8"))
    except Exception as e: print("硬失败：无法读取底稿：",e); return 2
    fail=[]
    for block,keys in 必需顶层.items():
        o=d.get(block)
        if not isinstance(o,dict): fail.append(f"缺少底稿区块：{block}"); continue
        for k in keys:
            if not o.get(k): fail.append(f"{block}缺少：{k}")
    comp=d.get("事实与竞争",{}).get("竞品价格口径",[])
    if not isinstance(comp,list) or len(comp)<2: fail.append("竞品价格口径少于2个项目")
    for x in comp if isinstance(comp,list) else []:
        if not isinstance(x,dict) or not all(x.get(k) for k in ("项目","价格","口径","来源","日期")): fail.append("存在不完整竞品价格记录"); break
    cards=d.get("客户资金",{}).get("客户卡",[])
    if not isinstance(cards,list) or len(cards)<3: fail.append("客户资金卡少于3张")
    for x in cards if isinstance(cards,list) else []:
        if not isinstance(x,dict) or any(not x.get(k) for k in 客户字段): fail.append("存在字段不全的客户资金卡"); break
    core=d.get("经营价格",{})
    try:
        if float(core["推荐首开成交价"]) < float(core["现金流安全售价"]): fail.append("推荐首开成交价低于现金流安全售价")
    except Exception: fail.append("经营价格必须使用可比较数字口径")
    try:
        收入=float(core["预计收入"]); 成本=float(core["总成本"]); 毛利=float(core["毛利额"])
        if abs((收入-成本)-毛利)>max(abs(毛利)*0.03,1):
            fail.append("预计收入-总成本与毛利额不勾稽")
        毛利率=float(str(core["毛利率"]).replace("%",""))
        计算率=(毛利/收入*100) if 收入 else 0
        if abs(毛利率-计算率)>2:
            fail.append("毛利率与预计收入、毛利额不勾稽")
    except Exception:
        fail.append("预计收入、总成本、毛利额、毛利率必须可勾稽")
    soul=d.get("精神内核",{})
    if soul.get("概念进化结论")!="通过": fail.append("概念进化结论必须为通过")
    if len(soul.get("四强差异",[]))!=4: fail.append("四强差异必须恰为4项")
    impact=soul.get("母题资格审查",{}).get("产品价格营销影响",[])
    if not isinstance(impact,list) or len(impact)<3: fail.append("主命题未改变至少3项产品价格营销动作")
    比较=d.get("产品预判营销",{}).get("产品结构比较",[])
    if not isinstance(比较,list) or len(比较)<2:
        fail.append("产品结构比较少于2种因果不同的产品情境")
    elif sum(1 for x in 比较 if isinstance(x,dict) and x.get("推荐结论"))!=1:
        fail.append("产品结构比较必须且只能有1项明确推荐结论")
    任务=d.get("产品预判营销",{}).get("客群空间任务",[])
    if not isinstance(任务,list) or len(任务)<8:
        fail.append("客群空间任务少于8项，无法证明户型、房间与公区来自客群反推")
    else:
        字段=("目标人物","发生时刻","当前代价","产品空间答案","尺度性能参数","成本工程边界","支付去化作用","验证停止条件")
        for i,x in enumerate(任务,1):
            if not isinstance(x,dict) or any(not x.get(k) for k in 字段):
                fail.append(f"客群空间任务{i}字段不完整"); break
    战役=d.get("产品预判营销",{}).get("首开战役",[])
    if not isinstance(战役,list) or len(战役)<8:
        fail.append("首开战役少于8个时间窗")
    运行=d.get("产品预判营销",{}).get("开盘日运行",{})
    if not isinstance(运行,dict) or any(not 运行.get(k) for k in ("时间轴","空间流线","系统与备份","岗位责任","实时数据","应急预案")):
        fail.append("开盘日运行缺少时间轴、流线、系统、岗位、数据或应急")
    # 产品结构面积占比与经营敏感性三情境概率合计；三情境不是产品模板
    import re as _re
    prod=d.get("产品预判营销",{}).get("产品结构",[])
    if isinstance(prod,list) and prod:
        占比=[]
        for x in prod:
            m=_re.search(r"(\d+(?:\.\d+)?)\s*%",str(x.get("面积占比","")) if isinstance(x,dict) else "")
            if m: 占比.append(float(m.group(1)))
        if 占比 and not 95<=sum(占比)<=105: fail.append(f"产品结构面积占比合计{sum(占比):g}%，须在95—105之间")
    情境=d.get("产品预判营销",{}).get("三情境",{})
    if isinstance(情境,dict) and 情境:
        概率=[]
        for v in 情境.values():
            m=_re.search(r"(\d+(?:\.\d+)?)\s*%",str(v.get("概率级别","")) if isinstance(v,dict) else "")
            if m: 概率.append(float(m.group(1)))
        if 概率 and not 95<=sum(概率)<=105: fail.append(f"三情境概率合计{sum(概率):g}%，须在95—105之间")
    if fail:
        print("交付审查关：未通过"); [print("- "+x) for x in dict.fromkeys(fail)]; return 1
    print("交付审查关：通过；允许进入页面编排。"); return 0
if __name__=="__main__": sys.exit(main())
