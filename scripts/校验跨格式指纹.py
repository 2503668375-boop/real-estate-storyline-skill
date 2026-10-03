#!/usr/bin/env python3
"""校验HTML、PPTX、PDF可提取文字中是否嵌入同一内容指纹。"""
from __future__ import annotations
import argparse,hashlib,json,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path

def 期望(p):
 d=json.loads(p.read_text(encoding="utf-8"));fp=d.get("内容指纹","");q=dict(d);q.pop("内容指纹",None)
 true=hashlib.sha256(json.dumps(q,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 return fp if fp==true else ""
def 提取(p):
 if p.suffix.lower()==".pptx":
  with zipfile.ZipFile(p) as z:return "".join(z.read(n).decode("utf-8","ignore") for n in z.namelist() if n.endswith(".xml"))
 if p.suffix.lower()==".pdf":
  exe=shutil.which("pdftotext")
  if not exe:return ""
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/"x.txt";subprocess.run([exe,str(p),str(out)],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   return out.read_text(encoding="utf-8",errors="ignore") if out.exists() else ""
 return p.read_text(encoding="utf-8",errors="ignore")
def main():
 p=argparse.ArgumentParser();p.add_argument("底稿",type=Path);p.add_argument("交付文件",type=Path,nargs="+");a=p.parse_args();fp=期望(a.底稿)
 if not fp:print("硬失败：底稿指纹无效");return 2
 bad=[]
 for f in a.交付文件:
  if not f.is_file() or fp not in 提取(f):bad.append(str(f))
 if bad:
  print("硬失败：以下文件未检出同一内容指纹：")
  for x in bad:print("- "+x)
  return 1
 print("跨格式内容指纹一致。");return 0
if __name__=="__main__":sys.exit(main())

