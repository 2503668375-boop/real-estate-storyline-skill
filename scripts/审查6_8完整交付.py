#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按8.1前策因果、价值叙事、整合营销与外部提案规则运行完整HTML交付审查。"""
import argparse, subprocess, sys
from pathlib import Path

根=Path(__file__).resolve().parent
def 跑(名称,参数):
    print("\n["+名称+"]")
    r=subprocess.run([sys.executable,str(根/参数[0])]+[str(x) for x in 参数[1:]])
    if r.returncode: print("总审查关：停止在 "+名称); return r.returncode
    return 0
def main():
    p=argparse.ArgumentParser(); p.add_argument("--研究",type=Path,required=True); p.add_argument("--概念进化",type=Path,required=True); p.add_argument("--主线",type=Path,required=True); p.add_argument("--价值推导",type=Path,required=True); p.add_argument("--文学主线",type=Path,required=True); p.add_argument("--人文传播",type=Path,required=True); p.add_argument("--故事线",type=Path,required=True); p.add_argument("--经营",type=Path,required=True); p.add_argument("--全周期营销",type=Path,required=True); p.add_argument("--视觉",type=Path,required=True); p.add_argument("--一页纸",type=Path,required=True); p.add_argument("--HTML",type=Path,required=True); p.add_argument("--项目名",required=True); p.add_argument("--有标杆",action="store_true"); p.add_argument("--要求精神引文",action="store_true"); a=p.parse_args()
    story_args=["审查故事线母题.py",a.故事线]+(["--有标杆"] if a.有标杆 else [])+(["--要求精神引文"] if a.要求精神引文 else [])
    steps=[("研究底盘",["审查研究底稿.py",a.研究]),("概念进化",["审查概念进化.py",a.概念进化]),("逻辑主线",["审查逻辑主线.py",a.主线]),("价值推导",["审查价值推导链.py",a.价值推导,"--类型","完整"]),("文学主线",["审查文学主线.py",a.文学主线]),("人文传播",["审查人文传播链.py",a.人文传播]),("故事线导演",story_args),("概念新颖性",["审查概念新颖性.py",a.故事线]),("经营价格",["审查交付闸门.py",a.经营,"--类型","完整"]),("首开营销",["审查营销调性.py",a.经营,"--故事线",a.故事线]),("全周期营销",["审查全周期营销.py",a.全周期营销]),("视觉策略",["审查视觉策略.py",a.视觉]),("一页战略总纲",["审查一页价值体系.py",a.一页纸,"--写入指纹"]),("外部完整提案",["审查外部完整提案.py",a.HTML,"--类型","完整"]),("HTML内容格式",["审查HTML汇报.py",a.HTML,"--类型","完整","--项目名",a.项目名,"--底稿",a.一页纸]),("中国语境与页面有效性",["审查中国语境与页面有效性.py",a.HTML]),("HTML运行前置",["审查HTML运行.py",a.HTML,"--最少页数","70"])]
    for name,args in steps:
        code=跑(name,args)
        if code:return code
    print("\n内部底稿与外部成品自动审查全部通过；仍须真实浏览器逐页渲染、缩略图总览，并按甲方视角人工逐页检查。")
    return 0
if __name__=="__main__": sys.exit(main())
