#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""9.0外部提案内容实质审查：阻断字段填充、空洞正文和视觉占位。"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from collections import Counter
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
规则 = json.loads((根 / "references" / "统一规则.json").read_text(encoding="utf-8"))
页面类型映射 = {"证据":"evidence", "决策":"decision", "产品证明":"product-proof", "客户原声":"customer-voice", "运营动作":"operation", "概念":"concept", "附录":"appendix"}

def norm(x: str) -> str:
    return re.sub(r"\s+", "", x or "")

class Deck(HTMLParser):
    void = {"img", "meta", "link", "input", "br", "hr", "source", "path", "rect", "circle", "polyline", "line"}
    非正文类 = {"footer", "eyebrow", "proof-line", "fact-line", "source-line", "visual-caption", "chart-note", "chapter-note", "page-number"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pages, self.now, self.depth, self.ignore, self.in_title = [], None, 0, 0, 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs); classes = (a.get("class") or "").split()
        if self.now is None and "slide" in classes:
            self.now = {"attrs": a, "text": [], "main": [], "head": [], "tags": [], "classes": [], "visual": 0, "svg_nodes": 0, "stack": [(tag, False)], "skip": 0}
            self.depth = 1
        elif self.now is not None and tag not in self.void:
            self.depth += 1
        if self.now is not None:
            self.now["tags"].append(tag)
            self.now["classes"].extend(classes)
            if tag in {"img", "canvas", "table"}: self.now["visual"] += 1
            if tag == "svg": self.now["visual"] += 1
            if tag in {"path", "rect", "circle", "polyline", "line", "text"}: self.now["svg_nodes"] += 1
            if tag in {"h1", "h2", "h3"}: self.in_title += 1
            if tag not in self.void and not (self.depth == 1 and "slide" in classes):
                skip = bool(set(classes) & self.非正文类) or tag == "footer"
                self.now["stack"].append((tag, skip))
                if skip: self.now["skip"] += 1
        if tag in {"script", "style"}: self.ignore += 1
    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.ignore: self.ignore -= 1
        if self.now is not None and tag not in self.void:
            if tag in {"h1", "h2", "h3"} and self.in_title: self.in_title -= 1
            if self.now["stack"]:
                _, skip = self.now["stack"].pop()
                if skip: self.now["skip"] -= 1
            self.depth -= 1
            if self.depth == 0:
                self.pages.append(self.now); self.now = None
    def handle_data(self, data):
        if self.now is not None and not self.ignore:
            self.now["text"].append(data)
            if self.in_title: self.now["head"].append(data)
            if not self.in_title and not self.now["skip"]: self.now["main"].append(data)

def load_manifest(path: Path):
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"页面事实清单无法读取：{exc}"]
    err=[]
    if d.get("版本") != "9.0": err.append("页面事实清单版本必须为9.0")
    pages=d.get("页面", [])
    if not isinstance(pages, list) or not pages: err.append("页面事实清单缺少页面列表")
    return d, err

def skeleton(p):
    raw="|".join(p["tags"])+"#"+"|".join(x for x in p["classes"] if x not in {"active","visible","reveal"})
    return hashlib.sha1(raw.encode()).hexdigest()

def audit(html_path: Path, manifest_path: Path, screenshots: Path | None, 需要截图: bool = True):
    raw=html_path.read_text(encoding="utf-8")
    parser=Deck(); parser.feed(raw); pages=parser.pages
    manifest, fail=load_manifest(manifest_path)
    if not pages: return ["未识别到slide页面"], []
    if manifest is None: return fail, []
    records=manifest.get("页面", []) if isinstance(manifest,dict) else []
    if len(records)!=len(pages): fail.append(f"页面事实清单{len(records)}页，与HTML{len(pages)}页不一致")
    by_no={x.get("页码"):x for x in records if isinstance(x,dict)}
    body_norm=[]; structures=[]; decisions=[]; actions=[]; source_sets=[]; evidence_ids=[]
    warnings=[]
    for i,p in enumerate(pages,1):
        a=p["attrs"]; text=norm("".join(p["text"])); main=norm("".join(p["main"])); title=norm("".join(p["head"]))
        section=a.get("data-section", "")
        if section=="appendix": continue
        rec=by_no.get(i)
        if not isinstance(rec,dict): fail.append(f"第{i}页未绑定页面事实清单"); continue
        for key, minimum in (("标题",6),("核心断言",12),("页面类型",1),("证据单元",1),("事实",1),("可见证据",1),("解释",16),("项目后果",12),("项目锚点",1),("来源",1),("视觉任务",4),("视觉材料类型",2),("视觉问题",6)):
            value=rec.get(key)
            if isinstance(value,list): ok=len(value)>=minimum
            else: ok=len(norm(str(value)))>=minimum
            if not ok: fail.append(f"页面事实清单第{i}页缺少{key}")
        page_kind = 页面类型映射.get(str(rec.get("页面类型", "")), str(rec.get("页面类型", "")))
        if page_kind not in 规则["外部页面类型"]: fail.append(f"页面事实清单第{i}页页面类型无效")
        elif a.get("data-page-kind") != page_kind: fail.append(f"第{i}页页面类型与HTML属性不一致")
        if norm(str(rec.get("标题",""))) not in title:
            fail.append(f"第{i}页标题未与页面事实清单绑定")
        facts=rec.get("事实",[]) if isinstance(rec.get("事实"),list) else []
        anchors=rec.get("项目锚点",[]) if isinstance(rec.get("项目锚点"),list) else []
        visible=rec.get("可见证据",[]) if isinstance(rec.get("可见证据"),list) else [rec.get("可见证据","")]
        if not any(norm(str(x)) in main for x in facts): fail.append(f"第{i}页正文没有呈现其声明的可核验事实")
        if not any(norm(str(x)) in main for x in visible): fail.append(f"第{i}页正文没有呈现可见证据")
        if not any(norm(str(x)) in text for x in anchors): fail.append(f"第{i}页缺少项目专属锚点")
        for field, label in (("解释","解释"),("项目后果","项目后果")):
            value=rec.get(field, "")
            if norm(str(value)) not in main: fail.append(f"第{i}页正文没有呈现{label}")
        units=rec.get("证据单元",[]) if isinstance(rec.get("证据单元"),list) else []
        unit_ids=[]
        for unit in units:
            if not isinstance(unit,dict) or not norm(unit.get("ID")) or not norm(unit.get("类型")) or not norm(unit.get("来源ID")):
                fail.append(f"页面事实清单第{i}页证据单元缺少ID、类型或来源ID"); continue
            unit_ids.append(norm(unit["ID"]))
        attr_evidence=[x.strip() for x in a.get("data-evidence-id","").split(",") if x.strip()]
        if unit_ids and not set(unit_ids).issubset(set(attr_evidence)): fail.append(f"第{i}页证据单元与HTML属性不一致")
        evidence_ids.extend((i,x,section) for x in unit_ids)
        declared=rec.get("来源",[]) if isinstance(rec.get("来源"),list) else []
        attr_sources=[x.strip() for x in a.get("data-source-id","").split(",") if x.strip()]
        if len(attr_sources)>4: fail.append(f"第{i}页登记了{len(attr_sources)}个来源，属于来源撒网，未指向本页事实")
        if declared and not set(declared).issubset(set(attr_sources)): fail.append(f"第{i}页来源属性与事实清单不一致")
        if p["visual"]==0 or ("svg" in p["tags"] and p["svg_nodes"]<3): fail.append(f"第{i}页没有承担证明任务的视觉材料")
        visual_type=norm(str(rec.get("视觉材料类型", "")))
        if visual_type in {"数据图","比较表","经营表"} and not ({"svg","canvas","table"} & set(p["tags"])): fail.append(f"第{i}页声明{visual_type}却没有数据图或表")
        if visual_type in {"总图/图纸","实拍"} and "img" not in p["tags"]: fail.append(f"第{i}页声明{visual_type}却没有图片/图纸")
        if p["classes"].count("mark"): fail.append(f"第{i}页使用编号圆环作为主视觉占位")
        minimum = 45 if page_kind in {"decision","concept"} else 70
        if len(main)<minimum: fail.append(f"第{i}页标题之外的正文不足{minimum}字，属于用标题或注脚填页")
        cleaned=main
        for x in [title, "来源", "负责人", "参数", "动作"]: cleaned=cleaned.replace(x, "")
        body_norm.append((i,cleaned)); structures.append((i,skeleton(p)))
        decisions.append(a.get("data-decision", "")); actions.append(a.get("data-action", "")); source_sets.append(a.get("data-source-id", ""))
    for n in range(len(body_norm)):
        for m in range(n):
            a,b=body_norm[n],body_norm[m]
            if min(len(a[1]),len(b[1]))>80 and SequenceMatcher(None,a[1],b[1]).ratio()>=.82:
                fail.append(f"第{b[0]}与第{a[0]}页正文高度重复，属于换标题填页"); break
    sc=Counter(x[1] for x in structures)
    for sig,count in sc.items():
        if count>max(5, len(structures)//4): fail.append(f"{count}页共用同一DOM骨架，版式重复超过完整提案上限")
    for label, vals in (("决定",decisions),("来源集合",source_sets)):
        vals=[x for x in vals if x]
        if vals and Counter(vals).most_common(1)[0][1]>max(4,len(vals)//3): fail.append(f"{label}元数据大面积复用，不能证明页面责任真实存在")
    for eid, count in Counter(x[1] for x in evidence_ids).items():
        sections={x[2] for x in evidence_ids if x[1]==eid}
        limit=规则["页面证据复用上限"]["市场"] if "market" in sections else 规则["页面证据复用上限"]["竞品"] if "competition" in sections else 规则["页面证据复用上限"]["默认"]
        if count>limit: fail.append(f"证据单元{eid}被复用{count}页，超过{limit}页上限，属于拆句补页")
    if not 需要截图:
        warnings.append("演示版：已跳过逐页截图视觉验收，以结构与内容审查为准")
    elif screenshots is None or not screenshots.is_dir():
        fail.append("缺少逐页渲染截图目录；DOM检查不能替代视觉验收")
    else:
        images=[p for p in screenshots.iterdir() if not p.name.startswith("._") and p.suffix.lower() in {".png",".jpg",".jpeg",".webp"}]
        if len(images)!=len(pages): fail.append(f"逐页截图{len(images)}张，与HTML{len(pages)}页不一致")
    return list(dict.fromkeys(fail)), warnings

def demo(tmp: Path):
    html=tmp/"fake.html"; facts=tmp/"页面事实清单.json"; shots=tmp/"shots"; shots.mkdir(exist_ok=True)
    good="光明区2025年1—4月新建商品住宅网签2139套，同比增加148%。这说明区级成交回升，但不能代替马田项目的去化判断。首批货量按竞品余货和转认筹共同校准。"
    html.write_text("<html><body><section class='slide' data-section='market' data-page-kind='evidence' data-source-id='S01' data-evidence-id='M-01' data-decision='按竞品余货校准首批货量' data-action='复核竞品余货'><h1>区级回升不等于项目可以放量</h1><p>"+good+"</p><p>项目锚点：光明区马田街道。</p><svg><path/><path/><path/></svg></section></body></html>",encoding="utf-8")
    valid={"版本":"9.0","页面":[{"页码":1,"标题":"区级回升不等于项目可以放量","核心断言":"区级成交回升不能直接替代马田项目的去化判断","页面类型":"evidence","证据单元":[{"ID":"M-01","类型":"数据","来源ID":"S01"}],"事实":["光明区2025年1—4月新建商品住宅网签2139套，同比增加148%"],"可见证据":["光明区2025年1—4月新建商品住宅网签2139套，同比增加148%"],"解释":"这说明区级成交回升，但不能代替马田项目的去化判断。","项目后果":"首批货量按竞品余货和转认筹共同校准。","项目锚点":["光明区马田街道"],"来源":["S01"],"视觉任务":"比较区级成交与项目推货边界","视觉材料类型":"数据图","视觉问题":"区级回升能否直接推导项目放量"}]}
    facts.write_text(json.dumps(valid,ensure_ascii=False),encoding="utf-8"); (shots/"001.png").write_bytes(b"x")
    assert not audit(html,facts,shots)[0], "有效页面内容合同未通过"
    shared="同一段字反复出现，用关键词满足字段检查，但没有任何项目事实或实际证明。"
    html.write_text("<html><body>"+"".join(f"<section class='slide' data-section='market' data-source-id='S01,S02,S03,S04,S05' data-decision='同一决定' data-action='同一动作'><h1>第{i}页标题</h1><p>{shared}</p><div class='mark'>0{i}</div></section>" for i in range(1,7))+"</body></html>",encoding="utf-8")
    facts.write_text(json.dumps({"版本":"9.0","页面":[{"页码":i,"标题":f"第{i}页标题","核心断言":"同一段空泛断言无法成立","页面类型":"evidence","证据单元":[{"ID":"E-01","类型":"数据","来源ID":"S01"}],"事实":["不存在事实"],"可见证据":["不存在事实"],"解释":"这条事实无法解释标题","项目后果":"必须改变真实项目决定","项目锚点":["不存在锚点"],"来源":["S01"],"视觉任务":"证明项目差异","视觉材料类型":"数据图","视觉问题":"比较真实项目差异"} for i in range(1,7)]},ensure_ascii=False),encoding="utf-8")
    bad,_=audit(html,facts,shots)
    assert bad and any("换标题填页" in x or "圆环" in x or "来源撒网" in x for x in bad), "关键词填充回归样本未被拦截"
    print("内容实质审查自检通过：有效内容合同可通过，关键词填充、圆环占位与来源撒网样本被拒绝。")

def main():
    ap=argparse.ArgumentParser(description="9.0内容实质与视觉验收审查")
    ap.add_argument("HTML",type=Path,nargs="?"); ap.add_argument("--页面事实",type=Path); ap.add_argument("--截图目录",type=Path); ap.add_argument("--演示",action="store_true"); ap.add_argument("--自检",action="store_true")
    a=ap.parse_args()
    if a.自检:
        import tempfile
        with tempfile.TemporaryDirectory() as d: demo(Path(d))
        return 0
    if not a.HTML or not a.页面事实: ap.error("必须提供HTML与--页面事实")
    fail,warn=audit(a.HTML,a.页面事实,a.截图目录,需要截图=not a.演示)
    print(f"内容实质审查：{a.HTML}")
    for x in warn: print("提醒："+x)
    if fail:
        print("未通过："); [print("- "+x) for x in fail]; return 1
    print("通过：页面证据、解释、项目后果、视觉证明、版式差异和逐页截图均已核验。")
    return 0
if __name__=="__main__": sys.exit(main())
