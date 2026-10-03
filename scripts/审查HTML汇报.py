#!/usr/bin/env python3
"""按统一规则审查构建后的地产汇报HTML。"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlparse

根=Path(__file__).resolve().parents[1]
规则=json.loads((根/"references"/"统一规则.json").read_text(encoding="utf-8"))

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.原型=[]; self.主线=[]; self.视觉角色=[]; self.资源=[]; self.表格=0; self.标题=[]; self.正文=[]; self.标题中=False; self.正文中=False; self.忽略=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs); c=set((a.get("class") or "").split())
        if 规则["HTML页面类"] in c:
            self.原型.append((a.get("data-prototype") or "").strip())
            self.主线.append((a.get(规则.get("HTML主线属性","data-proof-node")) or "").strip())
            self.视觉角色.append((a.get(规则.get("HTML视觉角色属性","data-visual-role")) or "").strip())
        if tag=="title":self.标题中=True
        if tag=="body":self.正文中=True
        if tag in {"script","style"}:self.忽略+=1
        if tag=="table":self.表格+=1
        for k in ("src","href","poster"):
            if a.get(k):self.资源.append(a[k])
    def handle_endtag(self,tag):
        if tag=="title":self.标题中=False
        if tag=="body":self.正文中=False
        if tag in {"script","style"} and self.忽略:self.忽略-=1
    def handle_data(self,d):
        if self.标题中:self.标题.append(d)
        elif self.正文中 and not self.忽略:self.正文.append(d)

def 最长同类(a):
    m=n=0; old=None
    for x in a:
        n=n+1 if x==old else 1; old=x; m=max(m,n)
    return m

def 底稿指纹(p):
    d=json.loads(p.read_text(encoding="utf-8")); fp=d.get("内容指纹","")
    副=dict(d); 副.pop("内容指纹",None)
    真=hashlib.sha256(json.dumps(副,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return fp if fp==真 else ""

def 主程序():
    p=argparse.ArgumentParser(); p.add_argument("入口",type=Path); p.add_argument("--类型",required=True,choices=规则["交付页数"]); p.add_argument("--项目名",required=True); p.add_argument("--底稿",type=Path); a=p.parse_args()
    if not a.入口.is_file() or a.入口.suffix.lower() not in {".html",".htm"}:print("不通过：必须传入构建后的HTML入口");return 2
    try:t=a.入口.read_text(encoding="utf-8",errors="strict")
    except UnicodeDecodeError:print("不通过：HTML不是有效UTF-8");return 2
    low=t.lower(); clean=re.sub(r"<!--[\s\S]*?-->|/\*[\s\S]*?\*/","",low); dom=P(); dom.feed(t); 失败=[]; 警告=[]
    if any(x in t for x in ("�","Ã¤","Ã¥","â€™","â€œ")):失败.append("检测到乱码")
    if not re.search(r"<meta[^>]+charset\s*=\s*[\"']?utf-?8",low):失败.append("缺少UTF-8声明")
    if not re.search(r"<html[^>]+lang\s*=\s*[\"']zh(?:-cn)?[\"']",low):失败.append("缺少lang=zh-CN")
    n=len(dom.原型); lo,hi=规则["交付页数"][a.类型]
    if n>hi:失败.append(f"{a.类型}实际页面{n}，超过参考上限{hi}，应先合并重复内容")
    elif n<lo:
        if 规则.get("页数下限性质",{}).get(a.类型)=="参考":警告.append(f"{a.类型}实际页面{n}，低于参考区间{lo}—{hi}；应核对模块覆盖，但不得凑页")
        else:失败.append(f"{a.类型}实际页面{n}，应为{lo}—{hi}")
    if any(not x for x in dom.原型):失败.append("存在缺少data-prototype的页面")
    if a.类型=="完整" and any(not x for x in dom.主线):失败.append("存在缺少data-proof-node的页面")
    if a.类型=="完整" and any(not x for x in dom.视觉角色):失败.append("存在缺少data-visual-role的页面")
    kinds=set(x for x in dom.原型 if x)
    if len(kinds)<规则["最低页面原型数"][a.类型]:失败.append("页面原型种类不足")
    if 最长同类(dom.原型)>3:失败.append("同一页面原型连续超过3页")
    if a.类型 in {"完整","摘要","一页"} and 规则["HTML价值体系原型"] not in kinds:失败.append("缺少value-system一页纸")
    if a.类型=="完整":
        缺原型=[x for x in 规则.get("故事线HTML原型",[]) if x not in kinds]
        if 缺原型:失败.append("缺少故事线页面原型："+"、".join(缺原型))
        缺主线=[x for x in 规则.get("HTML主线节点",[]) if x not in set(dom.主线)]
        if 缺主线:失败.append("缺少主线节点："+"、".join(缺主线))
        非法角色=[x for x in set(dom.视觉角色) if x not in 规则.get("HTML视觉角色",[])]
        if 非法角色:失败.append("存在无效视觉角色："+"、".join(非法角色))
        if len(set(dom.视觉角色))<6:失败.append("视觉角色少于6类，发布会节奏不足")
    attr=规则["HTML舞台属性"]
    舞台=re.search(rf"\[{re.escape(attr)}\][^{{]*\{{([^}}]+)\}}",low)
    if not 舞台 or not re.search(r"width\s*:\s*1920px",舞台.group(1)) or not re.search(r"height\s*:\s*1080px",舞台.group(1)):失败.append(f"缺少公开规范[{attr}]的1920×1080舞台")
    if "transform-origin" not in low or not re.search(r"scale\s*\(",low):失败.append("缺少整体缩放")
    if re.search(r"@media[\s\S]{0,1200}(grid-template-columns\s*:\s*1fr|flex-direction\s*:\s*column|auto-fit|auto-fill)",clean):失败.append("媒体查询疑似重排")
    if not re.search(r"(?:\.slide\.active|\.slide\[data-active|\[data-active=[\"']true)[^{]*\{[^}]*animation",clean):失败.append("缺少活动页动画")
    if "@keyframes" not in low or "prefers-reduced-motion" not in low:失败.append("缺少关键帧或减弱动画降级")
    视觉=set()
    if re.search(r"<img\b",low):视觉.add("图片")
    if re.search(r"<svg\b",low):视觉.add("SVG")
    if re.search(r"<canvas\b|data-visual=",low):视觉.add("数据图")
    if re.search(r"background-image\s*:|linear-gradient\s*\(|radial-gradient\s*\(",low):视觉.add("背景纹理")
    if len(视觉)<2:失败.append("视觉元素不足两类，一个渐变不能通过")
    if a.类型=="完整" and not re.search(r"<img\b",low):失败.append("完整故事线缺少项目/人物/空间图片，不能只用CSS背景")
    if a.类型=="完整" and not re.search(r"<svg\b|<canvas\b|data-visual=",low):失败.append("完整故事线缺少空间原型、动线或数据原创图解")
    if dom.表格 and a.类型!="决策":失败.append(f"主汇报含{dom.表格}个HTML table，明细应放附件")
    外=set()
    for u in dom.资源+re.findall(r"url\(\s*[\"']?([^\"')]+)",t,re.I):
        if u.startswith(("http://","https://","//")):外.add(u)
        elif u and not u.startswith(("data:","blob:","#","javascript:")):
            q=unquote(urlparse(u).path)
            if q and not (a.入口.parent/q).exists():失败.append("相对资源不存在："+u)
    if 外:失败.append(f"存在{len(外)}个外网运行依赖")
    if a.项目名 not in "".join(dom.标题):失败.append("浏览器标题缺少项目名")
    if a.项目名 not in " ".join(dom.正文):失败.append("正文缺少项目名")
    if a.类型!="一页":
        if not re.search(r"arrowleft|arrowright|keydown",clean):失败.append("缺少键盘翻页")
        if not re.search(r"touchstart|pointerdown|swipe",clean):失败.append("缺少触摸翻页")
        if not re.search(r"(?:queryselectorall\([^)]*\.slide[^)]*\)|\bslides\b)\.length",clean):失败.append("未从DOM页面集合计算总页数")
    if re.search(r"\b(?:totalpages|pagetotal|总页数)\s*=\s*\d+\s*;",clean):失败.append("写死页码总数")
    if a.底稿:
        fp=底稿指纹(a.底稿)
        if not fp:失败.append("底稿内容指纹无效")
        elif not re.search(rf"<meta[^>]+name=[\"']value-system-hash[\"'][^>]+content=[\"']{fp}[\"']",low):失败.append("HTML未嵌入与底稿一致的内容指纹")
    print(f"HTML审查：页面{n}；原型{len(kinds)}；视觉{len(视觉)}类；外链{len(外)}")
    if 失败:
        print("\n不通过：")
        for x in dict.fromkeys(失败):print("- "+x)
    if 警告:
        print("\n提醒：")
        for x in dict.fromkeys(警告):print("- "+x)
    if not 失败:print("\n源码和DOM初筛通过；仍须逐页渲染验收。")
    return 1 if 失败 else 0
if __name__=="__main__":sys.exit(主程序())
