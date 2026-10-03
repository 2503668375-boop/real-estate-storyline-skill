#!/usr/bin/env python3
"""市场数据结构核验11.0：不以数量或机构名单代替真实证据。"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse

DIMENSIONS = {'城市基线','板块供求','二手置换','竞品开盘','竞品成交','项目法定'}
FIELDS = ['证据ID','维度','指标','数值','单位','统计期','地域','口径','来源机构','发布日期','抓取日期','证据级别','允许推断','对项目决定']

def valid_date(value):
    return dt.date.fromisoformat(str(value))

def 审查(path):
    try:
        d=json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:
        return ['无法读取市场数据包：'+str(exc)]
    errors=[]
    if d.get('版本') not in {'9.0','11.0'}: errors.append('不支持的版本')
    for key in ['项目','地域','统计截至']:
        if not d.get(key): errors.append('缺少'+key)
    try:
        asof=valid_date(d.get('统计截至'))
        if asof>dt.date.today(): errors.append('统计截至在未来，预测请放独立情景')
    except ValueError:
        errors.append('统计截至日期无效'); asof=dt.date.today()
    rows=d.get('数据')
    if not isinstance(rows,list) or not rows: return errors+['数据须为非空列表']
    seen=set(); facts=set(); dims=set()
    for i,row in enumerate(rows,1):
        label='第'+str(i)+'条'
        if not isinstance(row,dict): errors.append(label+'须为对象'); continue
        for key in FIELDS:
            if row.get(key) is None or str(row.get(key)).strip()=='': errors.append(label+'缺少'+key)
        eid=row.get('证据ID')
        if not isinstance(eid,str) or not eid.strip(): errors.append(label+'证据ID无效')
        elif eid in seen: errors.append('证据ID重复：'+eid)
        else: seen.add(eid)
        dims.add(str(row.get('维度')))
        if row.get('维度') not in DIMENSIONS: errors.append(label+'维度无效')
        for key in ('发布日期','抓取日期'):
            try:
                day=valid_date(row.get(key))
                if day>asof or day>dt.date.today(): errors.append(label+key+'在统计截至或当前日期之后')
            except ValueError: errors.append(label+key+'无效')
        try:
            if valid_date(row.get('发布日期'))>valid_date(row.get('抓取日期')): errors.append(label+'先抓取后发布')
        except ValueError: pass
        period=str(row.get('统计期',''))
        for match in re.finditer(r'(\d{4})[-年](\d{1,2})(?:月|\b)',period):
            year,month=map(int,match.groups())
            if not 1<=month<=12: errors.append(label+'统计期月份无效')
            elif year*12+month>asof.year*12+asof.month: errors.append(label+'统计期在未来')
        for year in re.findall(r'(\d{4})年',period):
            if int(year)>asof.year: errors.append(label+'统计期年份在未来')
        link=row.get('来源链接',''); sourcefile=row.get('来源文件')
        if link:
            u=urlparse(link); host=(u.hostname or '').lower()
            if u.scheme not in {'http','https'} or not host: errors.append(label+'来源链接无效')
            if any(host==h or host.endswith('.'+h) for h in ['example.com','example.org','example.net','invalid','localhost']) or host.endswith(('.invalid','.test')):
                errors.append(label+'使用占位来源地址')
        elif not sourcefile: errors.append(label+'缺来源链接或来源文件')
        if sourcefile:
            p=Path(sourcefile)
            if not p.is_absolute(): p=Path(path).parent/p
            if not p.is_file(): errors.append(label+'来源文件不存在')
        signature=tuple(str(row.get(k,'')) for k in ['来源链接','来源文件','指标','地域','统计期','数值'])
        if signature in facts: errors.append(label+'与其它记录重复同一事实')
        facts.add(signature)
    if d.get('用途','完整前策')=='完整前策':
        missing=DIMENSIONS-dims
        if missing: errors.append('完整前策缺维度：'+'、'.join(sorted(missing)))
    return list(dict.fromkeys(errors))

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('数据包',type=Path); a=p.parse_args()
    errors=审查(a.数据包)
    if errors:
        print('未通过：'); [print('- '+x) for x in errors]; return 1
    print('结构通过；未由脚本联网证实来源内容、独立性或市场结论。继续核对证据台账与原文。')
    return 0
if __name__=='__main__': raise SystemExit(main())

