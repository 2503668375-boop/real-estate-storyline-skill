#!/usr/bin/env python3
"""11.0 分项交付核验。机器检查与真人/市场验证状态分开。"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parent

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.parts=[]; self.hidden=0
    def handle_starttag(self, tag, attrs):
        if tag in {'script','style'}: self.hidden+=1
    def handle_endtag(self, tag):
        if tag in {'script','style'} and self.hidden: self.hidden-=1
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)

def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def audit(folder):
    folder=Path(folder)
    errors=[]; warnings=[]; sections={}
    def read(name):
        try:
            obj=json.loads((folder/name).read_text(encoding='utf-8'))
            if not isinstance(obj,dict): raise ValueError('顶层须为对象')
            return obj
        except (OSError,ValueError) as exc:
            errors.append(name+'：'+str(exc)); return {}
    def require(row, fields, label):
        if not isinstance(row,dict):
            errors.append(label+'须为对象'); return False
        for key in fields:
            if key not in row or row[key] is None or row[key]=='' or row[key]==[]:
                errors.append(label+'缺少'+key)
        return True
    card=read('项目决策卡.json')
    require(card,['版本','项目','基准日','阶段','本轮任务','目标优先级','可改项','锁定项','需输出模块','责任人与权限','决策状态'], '项目决策卡')
    if card.get('版本')!='11.0': errors.append('项目决策卡版本须为11.0')
    try:
        asof=dt.date.fromisoformat(card.get('基准日',''))
        if asof>dt.date.today(): errors.append('项目基准日在未来')
    except (ValueError,TypeError):
        errors.append('项目基准日无效'); asof=dt.date.today()
    modes=card.get('需输出模块',[])
    if not isinstance(modes,list) or not modes or any(x not in {'市场','经营','价值','操盘','成品'} for x in modes):
        errors.append('需输出模块无效'); modes=[]
    ledger=read('证据台账.json')
    records=ledger.get('证据',[])
    if not isinstance(records,list) or not records:
        errors.append('证据台账须有证据列表'); records=[]
    indexed={}
    for n,e in enumerate(records,1):
        label='证据'+str(n)
        if not require(e,['ID','主张','类型','状态','日期','适用范围','来源文件'],label): continue
        eid=e.get('ID')
        if not isinstance(eid,str) or eid in indexed: errors.append(label+'ID无效或重复'); continue
        indexed[eid]=e
        if e.get('状态') not in {'已核验','待核验','冲突','估算','已失效'}: errors.append(label+'状态无效')
        try:
            if dt.date.fromisoformat(e.get('日期',''))>asof: errors.append(label+'证据日期晚于基准日')
        except (ValueError,TypeError): errors.append(label+'日期无效')
        p=Path(e.get('来源文件') or '__missing__')
        if not p.is_absolute(): p=folder/p
        if not p.is_file(): errors.append(label+'来源文件不存在')
        elif e.get('状态')=='已核验':
            require(e,['SHA256','原文摘录','核验人','核验日'],label)
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            if e.get('SHA256')!=digest: errors.append(label+'来源文件指纹不符')
            if p.suffix.lower() in {'.txt','.md','.csv','.json','.html'}:
                raw=p.read_text(encoding='utf-8',errors='replace')
                if str(e.get('原文摘录','')).strip() not in raw: errors.append(label+'摘录不在来源文件')
            try:
                check=dt.date.fromisoformat(e.get('核验日',''))
                if check>asof or check<dt.date.fromisoformat(e.get('日期','')): errors.append(label+'核验日时序错误')
            except (ValueError,TypeError): errors.append(label+'核验日无效')
        if e.get('状态')!='已核验': warnings.append(str(eid)+'为'+str(e.get('状态'))+'，限制依赖结论')
    def refs(row,label):
        ids=row.get('证据ID',[])
        if not isinstance(ids,list) or not ids: errors.append(label+'须引用证据ID'); return []
        absent=[x for x in ids if not isinstance(x,str) or x not in indexed]
        if absent: errors.append(label+'引用不存在的证据ID')
        evidence=[indexed[x] for x in ids if isinstance(x,str) and x in indexed]
        try:
            use=dt.date.fromisoformat(row.get('适用日',card.get('基准日','')))
            for e in evidence:
                if e.get('生效日') and use<dt.date.fromisoformat(e['生效日']): errors.append(label+'提前使用未生效证据')
                if e.get('失效日') and use>dt.date.fromisoformat(e['失效日']): errors.append(label+'使用已到期证据')
        except (ValueError,TypeError): errors.append(label+'适用/生效/失效日期无效')
        return evidence
    if '市场' in modes:
        market=folder/'市场数据包.json'
        errors.extend(module('审查市场数据包').审查(market))
        if market.is_file():
            d=read('市场数据包.json')
            for row in d.get('数据',[]):
                if isinstance(row,dict) and row.get('证据ID') not in indexed: errors.append('市场数据证据未登记台账')
        sections['市场']='结构与证据引用检查；未自动验证市场因果'
    result=None
    if '经营' in modes:
        business=read('经营价格底稿.json')
        try:
            result=module('经营与操盘工具').calculate(business)
            sections['经营']=result
            for sc in business.get('情景',[]):
                if not sc.get('参数证据ID'): warnings.append(str(sc.get('名称'))+'未列参数证据ID，数值仍需来源复核')
                else: refs({'证据ID':sc['参数证据ID'],'适用日':sc.get('适用日',card.get('基准日'))},'经营情景'+str(sc.get('名称')))
                if card.get('阶段') in {'拿地','投前','拿地/投前'} and ('损益' not in sc or '全投资现金流' not in sc):
                    errors.append('拿地/投前情景须有损益及全投资现金流，不能只交月度现金')
        except (ValueError,KeyError,TypeError) as exc: errors.append('经营计算：'+str(exc))
    if '价值' in modes:
        value=read('价值决策底稿.json')
        rows=value.get('价值',[])
        if not isinstance(rows,list) or not rows: errors.append('缺价值卡'); rows=[]
        for i,v in enumerate(rows,1):
            label='价值'+str(i)
            if not require(v,['ID','主张','角色','目标客户','客户任务','可用机制','竞争替代','客户代价','项目取舍','成本兑现','溢价状态','表达方向','验证计划','失效条件'],label): continue
            evidence=refs(v,label)
            if v.get('角色') not in {'成交门槛','选择优势','溢价理由','记忆表达'}: errors.append(label+'角色无效')
            if v.get('溢价状态') not in {'不主张','待验证','有条件证据'}: errors.append(label+'溢价状态无效')
            if v.get('溢价状态')=='有条件证据':
                require(v,['选择证据','支付证据ID'],label)
                pid=v.get('支付证据ID')
                p=indexed.get(pid,{}) if isinstance(pid,str) else {}
                if p.get('状态')!='已核验' or p.get('类型') not in {'交易行为','带价选择测试'}:
                    errors.append(label+'溢价缺已核验的交易行为或带价选择测试')
                if pid not in v.get('证据ID',[]): errors.append(label+'支付证据须纳入引用')
        sections['价值']='因果字段及证据引用检查；创意与支付效果需独立评价'
    if '操盘' in modes:
        play=read('操盘底稿.json')
        actions=play.get('动作',[])
        if not isinstance(actions,list) or not actions: errors.append('缺操盘动作'); actions=[]
        for i,a in enumerate(actions,1):
            label='动作'+str(i)
            if not require(a,['ID','目标库存','主障碍','目标客户','作用机制','基准','备选','执行步骤','预算成本','现金影响','负责人','授权状态','观察窗口','观察分母','加码条件','停止条件','恢复条件','副作用'],label): continue
            refs(a,label)
        recommendation=play.get('推荐情景')
        if result:
            sc=next((s for s in result['情景'] if s['名称']==recommendation),None)
            if sc is None: errors.append('操盘推荐情景未对应经营情景')
            elif not sc['资金可行']:
                if card.get('决策状态')=='已批准': errors.append('已批准情景资金不可行')
                if not play.get('资金补足条件'): errors.append('推荐情景有资金缺口却未列补足条件')
                else: warnings.append('推荐为资金补足后的条件方案，不能声称已经可执行')
        sections['操盘']='动作及数值关联检查；未代替审批或执行'
    if '成品' in modes:
        qa=read('成品验收.json')
        require(qa,['文件','格式','SHA256','审阅人','逐项检查','状态'],'成品验收')
        p=folder/str(qa.get('文件','__missing__'))
        if not p.is_file(): errors.append('成品文件不存在')
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=qa.get('SHA256'): errors.append('成品指纹不符')
        if qa.get('状态')!='通过': warnings.append('成品仍待实际页面验收')
        for key in ['文字与事实','溢出遮挡','阅读顺序','图表口径']:
            if key not in qa.get('逐项检查',{}): errors.append('成品缺检查项：'+key)
        if qa.get('格式') in {'HTML','PPTX','PDF'}:
            pages=qa.get('页面',[])
            total=qa.get('总页数')
            if isinstance(total,bool) or not isinstance(total,int) or total<1 or not isinstance(pages,list) or total!=len(pages):
                errors.append('成品总页数与逐页记录不符')
            if not isinstance(pages,list) or not pages: errors.append('缺逐页截图记录')
            else:
                seen=set()
                for i,page in enumerate(pages,1):
                    if not isinstance(page,dict): errors.append('页图记录无效'); continue
                    if page.get('页码')!=i: errors.append('页码必须从1连续对应实际顺序')
                    p=folder/str(page.get('截图','__missing__'))
                    if not p.is_file() or p.stat().st_size<100: errors.append('页图缺失或无效'); continue
                    digest=hashlib.sha256(p.read_bytes()).hexdigest()
                    if digest!=page.get('SHA256'): errors.append('页图指纹不符')
                    if digest in seen: warnings.append('出现相同页图，需确认是否重复截图')
                    seen.add(digest)
        if qa.get('状态')=='通过' and any(x!='通过' for x in qa.get('逐项检查',{}).values()):
            errors.append('成品总状态通过但存在未通过的检查项')
        sections['成品']='核验文件与验收记录存在；视觉判断由记录责任人承担'
    review=card.get('策略复核',{})
    if card.get('技能版本')=='11.1' and ({'价值','成品'} & set(modes)):
        expression=read('表达验收.json')
        require(expression,['稿件文件','SHA256','复核人','复核类型','内容去AI','文学表达','重点句','修改记录','复述记录'],'表达验收')
        p=folder/str(expression.get('稿件文件','__missing__'))
        if not p.is_file(): errors.append('表达验收稿件不存在')
        else:
            if hashlib.sha256(p.read_bytes()).hexdigest()!=expression.get('SHA256'): errors.append('表达验收与当前稿件版本不一致')
            if p.suffix.lower() in {'.md','.txt','.html'}:
                raw=p.read_text(encoding='utf-8',errors='replace')
                if p.suffix.lower()=='.html':
                    parser=VisibleText();parser.feed(raw);raw=''.join(parser.parts)
                raw=re.sub(r'\s+','',raw)
                keylines=expression.get('重点句',[])
                if not isinstance(keylines,list) or any(not isinstance(x,str) or re.sub(r'\s+','',x) not in raw for x in keylines):
                    errors.append('重点句未对应实际稿件')
        if expression.get('复核类型') not in {'作者自审','独立代理','人工审阅','客户测试'}: errors.append('表达复核类型无效')
        if expression.get('内容去AI')!='通过' or expression.get('文学表达')!='通过': errors.append('内容去AI或文学表达尚未通过具名复核')
        if '成品' in modes:
            checks=qa.get('逐项检查',{})
            if checks.get('内容去AI')!='通过' or checks.get('页面去AI')!='通过': errors.append('成品尚未完成内容与页面去AI检查')
        sections['文学与去AI']= {'记录状态':'已读取','复核类型':expression.get('复核类型'),
                                '边界':'脚本核稿件与复核记录，不检测作者身份或生成AI率；语感和版式由实际审阅判断'}
    sections['策略复核']=review or {'状态':'未完成'}
    if review.get('状态')!='已复核': warnings.append('尚无完成的独立策略复核，不宣称市场或创意验收通过')
    if not errors: warnings.append('机器通过只表示记录、引用与计算检查完成，不证明原文真实、市场效果、审美或发布许可')
    return {'版本':'11.0','机器检查':'未通过' if errors else '通过','失败':list(dict.fromkeys(errors)),
            '提示':list(dict.fromkeys(warnings)),'分项':sections}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--目录',type=Path,default=Path('.'));p.add_argument('--输出',type=Path);p.add_argument('--项目名')
    a=p.parse_args(argv)
    try: result=audit(a.目录)
    except (ValueError,TypeError,KeyError,OSError) as exc:
        result={'机器检查':'未通过','失败':['输入结构异常：'+str(exc)]}
    text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
    if a.输出: a.输出.write_text(text+'\n',encoding='utf-8')
    print(text)
    return 1 if result['机器检查']=='未通过' else 0
if __name__=='__main__': raise SystemExit(main())
