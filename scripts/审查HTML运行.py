#!/usr/bin/env python3
"""审查静态HTML的首屏、翻页链接与运行前置条件；不替代真实浏览器验证。"""
import argparse, re, sys
from html.parser import HTMLParser
from pathlib import Path

class P(HTMLParser):
 def __init__(self): super().__init__(); self.slides=[]; self.links=[]; self.text=[]; self.hidden=0
 def handle_starttag(self,t,a):
  d=dict(a); c=(d.get("class") or "").split()
  if "slide" in c: self.slides.append(d.get("id"))
  if t=="a" and d.get("href"): self.links.append(d["href"])
  if d.get("hidden") is not None or "display:none" in (d.get("style") or "").replace(" ",""): self.hidden+=1
 def handle_endtag(self,t): pass
 def handle_data(self,d):
  if not self.hidden: self.text.append(d.strip())

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("html",type=Path); ap.add_argument("--最少页数",type=int,default=1); a=ap.parse_args()
 t=a.html.read_text(encoding="utf-8"); p=P(); p.feed(t); fail=[]
 if len(p.slides)<a.最少页数: fail.append(f"静态slide少于{a.最少页数}页（实际{len(p.slides)}）")
 if any(not x for x in p.slides): fail.append("存在无id静态页面")
 ids=set(p.slides); targets={x[1:] for x in p.links if x.startswith("#")}
 if len(targets & ids)<max(2,len(ids)-1): fail.append("静态上一页/下一页链接未覆盖页面")
 if not re.search(r"(?:ArrowRight|keydown|keypress)",t): fail.append("缺少键盘翻页逻辑")
 if not re.search(r"(?:touchstart|pointerdown|swipe)",t): fail.append("缺少触摸翻页逻辑")
 if len("".join(p.text))<200: fail.append("首屏或正文缺少可见文字")
 if re.search(r"const\s+slides\s*=\s*\[|innerHTML\s*=.*slides",t,re.S): fail.append("检测到运行时数组生成页面；完整交付必须静态DOM")
 if fail:
  print("HTML运行前置：未通过"); [print("- "+x) for x in fail]; return 1
 print(f"HTML运行前置：通过；静态页{len(p.slides)}，仍需真实浏览器逐页验收。")
if __name__=="__main__": sys.exit(main())
