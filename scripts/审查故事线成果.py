#!/usr/bin/env python3
"""11.2/11.3 交付、正文及引用关系；不代替论证、创意、事实或视觉判断。"""
from pathlib import Path
import json
import hashlib
import re

RESPONSIBILITIES={'专项建议','卖点体系','完整故事线','图文提案'}

def audit_outputs(folder,card,evidence_ids,errors,warnings,sections):
    folder=Path(folder)
    def fail(msg):errors.append(str(card.get('技能版本','11.2'))+'成果：'+msg)
    def read(name):
        try:
            obj=json.loads((folder/name).read_text(encoding='utf-8'))
            if not isinstance(obj,dict):raise ValueError('顶层须为对象')
            return obj
        except (OSError,ValueError) as exc:fail(name+'：'+str(exc));return {}
    def fields(row,names,label):
        if not isinstance(row,dict):fail(label+'须为对象');return False
        for k in names:
            if k not in row or row[k] is None or row[k]=='' or row[k]==[]:fail(label+'缺少'+k)
        return True
    def rows(obj,key,label,nonempty=True):
        r=obj.get(key)
        if not isinstance(r,list) or (nonempty and not r):fail(label+'须为'+('非空' if nonempty else '')+'列表');return []
        return r
    def index(items,label):
        d={}
        for r in items:
            if not isinstance(r,dict):fail(label+'记录须为对象');continue
            rid=r.get('ID')
            if not isinstance(rid,str) or not rid.strip() or rid in d:fail(label+'ID缺失或重复');continue
            d[rid]=r
        return d
    def links(row,key,pool,label,nonempty=True):
        vals=row.get(key)
        if not isinstance(vals,list) or (nonempty and not vals):fail(label+'的'+key+'须为'+('非空' if nonempty else '')+'列表');return []
        if any(not isinstance(v,str) or v not in pool for v in vals):fail(label+'的'+key+'存在未定义引用')
        if len([v for v in vals if isinstance(v,str)])!=len(set(v for v in vals if isinstance(v,str))):fail(label+'的'+key+'重复')
        return vals
    def file_hash(row,filekey,hashkey,label):
        val=row.get(filekey)
        if not isinstance(val,str) or not val:fail(label+'文件路径缺失');return
        p=Path(val)
        if not p.is_absolute():p=folder/p
        if not p.is_file() or p.stat().st_size==0:fail(label+'文件缺失或为空');return
        if hashlib.sha256(p.read_bytes()).hexdigest()!=row.get(hashkey):fail(label+'文件指纹不符')
    responsibilities=card.get('交付责任')
    if not isinstance(responsibilities,list) or not responsibilities or any(not isinstance(x,str) or x not in RESPONSIBILITIES for x in responsibilities):
        fail('交付责任须声明专项建议、卖点体系、完整故事线、图文提案中的适用项');return
    modes=card.get('需输出模块',[])
    need_story='完整故事线' in responsibilities or '故事线' in modes
    need_value=need_story or '卖点体系' in responsibilities
    if need_story and not {'价值','故事线'}<=set(modes):fail('完整故事线须同时包含价值与故事线模块')
    if need_value and '价值' not in modes:fail('卖点体系须包含价值模块')
    if '图文提案' in responsibilities and '成品' not in modes:fail('图文提案须包含成品模块')
    if need_value:
        value=read('价值决策底稿.json')
        values=index(rows(value,'价值','价值卡'),'价值卡')
        features=index(rows(value,'项目特征','项目特征'),'项目特征')
        for fid,f in features.items():
            fields(f,['事实','突出关系','适用范围','限制','客户意义'],'特征'+fid)
            links(f,'证据ID',evidence_ids,'特征'+fid)
        for vid,v in values.items():links(v,'特征ID',features,'价值'+vid)
        choice=value.get('卖点取舍',{})
        fields(choice,['核心购买理由','主卖点ID','推荐理由','主要反对理由','舍弃项'],'卖点取舍')
        if isinstance(choice,dict):
            main=choice.get('主卖点ID')
            if not isinstance(main,str) or main not in values:fail('主卖点ID未对应价值卡')
            if main in values and values[main].get('角色') in {'成交门槛','记忆表达'}:warnings.append('主卖点目前仅为门槛或记忆表达，需人工复核是否形成选择优势')
            support=links(choice,'支撑卖点ID',values,'卖点取舍',False)
            links(choice,'基础门槛ID',values,'卖点取舍',False)
            if main in support:fail('主卖点不能同时充当自己的支撑卖点')
        sections['卖点体系']='特征、价值与主次关系已检查；优先级是否合理需实际复核'
    if need_story:
        story=read('故事线底稿.json')
        fields(story,['定位','市场机会','推荐主题ID','推荐说明','验证状态'],'故事线')
        links(story,'市场证据ID',evidence_ids,'市场机会')
        dirs=index(rows(story,'主题方向','主题方向'),'主题方向')
        for tid,t in dirs.items():
            fields(t,['主题','核心判断','产品承接','视觉方向','成立条件','取舍理由'],'方向'+tid)
            links(t,'特征ID',features,'方向'+tid);links(t,'价值ID',values,'方向'+tid);links(t,'证据ID',evidence_ids,'方向'+tid)
        selected=story.get('推荐主题ID')
        if not isinstance(selected,str) or selected not in dirs:fail('推荐主题ID未对应主题方向')
        chapters=index(rows(story,'章节','章节链'),'章节')
        for cid,c in chapters.items():
            fields(c,['标题','核心判断','主题ID','图文任务','承接'],'章节'+cid)
            if c.get('主题ID')!=selected:fail('章节'+cid+'未承接推荐主题')
            links(c,'价值ID',values,'章节'+cid);links(c,'证据ID',evidence_ids,'章节'+cid)
        extensions=rows(story,'传播延展','传播延展')
        for i,e in enumerate(extensions,1):
            if not fields(e,['场景','受众','主题ID','表达','证明动作','下一步'],'延展'+str(i)):continue
            if e.get('主题ID')!=selected:fail('传播延展未承接推荐主题')
            links(e,'价值ID',values,'传播延展');links(e,'证据ID',evidence_ids,'传播延展')
        sections['故事线']='主题选择、章节链、证明与传播引用已检查；主题质量和客户效果未自动判断'
        if card.get('技能版本')=='11.3':
            start_errors=len(errors)
            review=read('论证展开审阅.json')
            fields(review,['稿件文件','SHA256','复核人','复核类型'],'论证展开审阅')
            file_hash(review,'稿件文件','SHA256','论证正文')
            raw=''
            val=review.get('稿件文件')
            if isinstance(val,str) and val.strip():
                p=Path(val)
                if not p.is_absolute():p=folder/p
                if p.suffix.lower() not in {'.txt','.md'}:fail('论证正文须为可读的UTF-8 TXT或Markdown')
                elif p.is_file():
                    try:raw=p.read_text(encoding='utf-8')
                    except (OSError,UnicodeError) as exc:fail('论证正文无法读取：'+str(exc))
            norm=lambda s:re.sub(r'\s+','',s)
            if not norm(raw):fail('论证正文为空白')
            expression=read('表达验收.json')
            if any(review.get(k)!=expression.get(k) for k in ['稿件文件','SHA256']):
                fail('论证展开与表达验收未指向同一版正文')
            if review.get('复核类型') not in {'作者自审','独立代理','人工审阅','客户测试'}:
                fail('论证展开复核类型无效')
            units=index(rows(review,'论证单元','论证单元'),'论证单元')
            dispositions={}
            for uid,u in units.items():
                fields(u,['问题','审阅结论','审阅意见'],'论证'+uid)
                for key in ['问题','审阅意见']:
                    if not isinstance(u.get(key),str) or not u[key].strip():fail('论证'+uid+'的'+key+'须为非空文字')
                links(u,'证据ID',evidence_ids,'论证'+uid)
                links(u,'章节ID',chapters,'论证'+uid)
                status=u.get('审阅结论')
                if not isinstance(status,str) or status not in {'已充分展开','有条件展开','未展开'}:fail('论证'+uid+'审阅结论无效')
                if status=='未展开':fail('论证'+uid+'尚未展开，不能报完整交付')
                if status=='有条件展开' and (not isinstance(u.get('条件与分叉'),str) or not u['条件与分叉'].strip()):
                    fail('论证'+uid+'缺少条件与分叉')
                dispositions[uid]=status
                excerpt=u.get('原文摘录')
                if not isinstance(excerpt,dict):fail('论证'+uid+'原文摘录须为对象');continue
                excerpts=[]
                for role in ['事实与边界','解释与比较','项目决策']:
                    text=excerpt.get(role)
                    if not isinstance(text,str) or not norm(text):fail('论证'+uid+'缺少有效摘录：'+role);continue
                    text=norm(text);excerpts.append(text)
                    if text not in norm(raw):fail('论证'+uid+'摘录不在当前正文：'+role)
                if len(excerpts)==3 and len(set(excerpts))==1:
                    fail('论证'+uid+'三类摘录完全相同，需实际展开后分别引用')
            coverage=rows(review,'任务覆盖','任务覆盖')
            covered=set()
            for i,item in enumerate(coverage,1):
                if not fields(item,['用户要求'],'任务覆盖'+str(i)):continue
                if not isinstance(item.get('用户要求'),str) or not item['用户要求'].strip():fail('任务覆盖须写明实际用户要求')
                covered.update(v for v in links(item,'论证ID',units,'任务覆盖'+str(i)) if isinstance(v,str))
            if set(units)-covered:fail('存在未说明任务用途的论证单元')
            chapter_links={}
            for cid,c in chapters.items():
                chapter_links[cid]=links(c,'论证ID',units,'章节'+cid)
            for uid,u in units.items():
                linked=u.get('章节ID')
                if not isinstance(linked,list):continue
                for cid in linked:
                    if isinstance(cid,str) and cid in chapters and uid not in chapter_links.get(cid,[]):
                        fail('论证'+uid+'与章节'+cid+'的引用不对称')
            for cid,ids in chapter_links.items():
                for uid in ids:
                    if isinstance(uid,str) and uid in units:
                        back=units[uid].get('章节ID')
                        if not isinstance(back,list) or cid not in back:fail('章节'+cid+'与论证'+uid+'的引用不对称')
            sections['正文关联检查']='未通过' if len(errors)>start_errors else '通过'
            sections['内容深度评定']={
                '状态':'未自动评定','记录复核人':review.get('复核人'),
                '记录复核类型':review.get('复核类型'),'记录结论':dispositions,
                '边界':'仅核正文和审阅记录关联；需按五项冷读实际判断，不以字数或字段齐全证明详实'}
            warnings.append('11.3论证记录不等于内容深度合格；须检查正文中的解释、比较、取舍与创作')
    if '图文提案' in responsibilities:
        qa=read('成品验收.json');content=read('页面内容记录.json')
        if content.get('成品SHA256')!=qa.get('SHA256') or not content.get('成品SHA256'):fail('页面内容记录未绑定当前成品')
        assets=index(rows(content,'素材','素材',False),'素材')
        allowed={'实景','航拍','图纸','数据图表','关系示意','概念图','品牌素材'}
        for aid,a in assets.items():
            fields(a,['类型','来源性质','来源说明','文件','SHA256'],'素材'+aid)
            if a.get('类型') not in allowed:fail('素材类型无效')
            if a.get('来源性质') not in {'项目事实','合成教学','创意示意'}:fail('素材来源性质无效')
            links(a,'证据ID',evidence_ids,'素材'+aid)
            file_hash(a,'文件','SHA256','素材'+aid)
        pages=rows(content,'页面','页面内容')
        if len(pages)!=qa.get('总页数'):fail('页面内容与成品总页数不符')
        for i,p in enumerate(pages,1):
            if not fields(p,['标题','核心判断','正文要点','视觉责任','图文作用','复核意见'],'页面'+str(i)):continue
            if p.get('页码')!=i:fail('页面内容页码须连续且对应成品')
            links(p,'证据ID',evidence_ids,'页面'+str(i))
            role=p.get('视觉责任')
            if role not in {'事实证据','关系解释','概念表达','文字决策'}:fail('页面视觉责任无效')
            linked=links(p,'素材ID',assets,'页面'+str(i),role!='文字决策')
            if role=='事实证据' and linked and all(assets.get(a,{}).get('类型') in {'概念图','品牌素材'} for a in linked):fail('事实证据页仅有概念图或品牌素材')
        sections['图文内容']='页面内容、素材和当前成品关联已检查；实际显示、信息充分和审美需逐页复核'
