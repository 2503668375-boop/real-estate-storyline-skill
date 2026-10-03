#!/usr/bin/env python3
"""审查商业、办公、产业园、综合体前策的经营数字底线。"""
from __future__ import annotations
import argparse,re,sys
from pathlib import Path

字段={
"产业园":["租金","售价","去化","入园率","租售比例","主力分割","主导产业","亩均","运营成本","招商周期"],
"办公":["租金","售价","空置率","净吸纳","标准层","分割","效率","停车","企业","迁移成本","招商周期"],
"商业":["租金","客流","转化率","坪效","空置率","租售比","业态","主力店","招商周期","开业"],
"综合体":["面积占比","货值占比","租金","售价","空置","去化","现金流","开发时序","协同"]
}
def 主程序():
 p=argparse.ArgumentParser();p.add_argument("文件",type=Path);p.add_argument("--业态",required=True,choices=字段);a=p.parse_args()
 try:t=a.文件.read_text(encoding="utf-8",errors="strict")
 except Exception as e:print(f"硬失败：{e}");return 2
 失败=[]
 for k in 字段[a.业态]:
  if not re.search(rf"{k}.{{0,80}}\d",t,re.S):失败.append(f"{k}缺少数字")
 for x in ("进取","基准","防守"):
  if x not in t:失败.append("缺少情境："+x)
 if a.业态=="综合体":
  for k in ("面积占比","货值占比"):
   vals=[float(x) for x in re.findall(rf"{k}.{{0,40}}?(\d+(?:\.\d+)?)\s*%",t)]
   if vals and abs(sum(vals)-100)>1:失败.append(f"{k}合计{sum(vals):g}%，不等于100%")
 print(f"{a.业态}经营审查")
 if 失败:
  print("\n硬失败：")
  for x in dict.fromkeys(失败):print("- "+x)
 else:print("\n通过非住宅数字底线审查；仍须人工核验口径。")
 return 1 if 失败 else 0
if __name__=="__main__":sys.exit(主程序())

