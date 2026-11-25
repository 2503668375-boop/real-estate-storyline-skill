#!/usr/bin/env python3
"""隔离合成回归：完整故事线、主次与引用、图文材料和版本绑定。"""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('base_tests',ROOT/'测试11版核心.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def read(p,n):return json.loads((p/n).read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def fixture(p):
    v=base.value_fixture(p);v.update({'角色':'选择优势','主张':'归家路径连接城市生活与内院停留','特征ID':['F1']})
    c=read(p,'项目决策卡.json');c.update({'技能版本':'11.2','本轮任务':'完整故事线合成教学','交付责任':['完整故事线'],'需输出模块':['价值','故事线']})
    base.write(p,'项目决策卡.json',c)
    base.write(p,'价值决策底稿.json',{'版本':'11.0','价值':[v],
        '项目特征':[{'ID':'F1','事实':'合成：外街与内院相连','突出关系':'归家路径的动静变化','适用范围':'教学设定','限制':'声环境未测试','客户意义':'方便外出与院中停留','证据ID':['E1']}],
        '卖点取舍':{'核心购买理由':'城市便利与院落日常相连','主卖点ID':'V1','推荐理由':'合成示例中的可用组合','支撑卖点ID':[],'基础门槛ID':[],'主要反对理由':'临街噪声未验证','舍弃项':'未选择资产回报主题，无证据'}})
    base.write(p,'故事线底稿.json',{'定位':'合成城市改善','市场机会':'教学假设：重视便利与停留','市场证据ID':['E1'],
        '推荐主题ID':'T1','推荐说明':'仅验证结构，未证明创意质量','验证状态':'合成教学，未做真实客研',
        '主题方向':[{'ID':'T1','主题':'城中有院，日常从容','核心判断':'将街区便利与院落生活相连','特征ID':['F1'],'价值ID':['V1'],'证据ID':['E1'],'产品承接':'两段归家路径','视觉方向':'外街到内院的连续图解','成立条件':'实际路径与开放管理成立','取舍理由':'排除收益主题，无支付证据'}],
        '章节':[{'ID':'C1','标题':'沿归家路径看项目','核心判断':'以空间关系证明组合','主题ID':'T1','价值ID':['V1'],'证据ID':['E1'],'图文任务':'示意路径','承接':'现场核对与下一步'}],
        '传播延展':[{'场景':'带看','受众':'教学家庭','主题ID':'T1','价值ID':['V1'],'证据ID':['E1'],'表达':'从街边走到院中','证明动作':'核路径与停留条件','下一步':'补声环境证据'}]})
    (p/'稿件.txt').write_text('合成教学：城中有院，日常从容。')
    base.write(p,'表达验收.json',{'稿件文件':'稿件.txt','SHA256':digest(p/'稿件.txt'),'复核人':'测试程序','复核类型':'作者自审','内容去AI':'通过','文学表达':'通过','重点句':['城中有院，日常从容。'],'修改记录':'隔离字段测试，不代表真实文学验收','复述记录':'无真实客户测试'})

def graphic(p):
    fixture(p);c=read(p,'项目决策卡.json');c['交付责任'].append('图文提案');c['需输出模块'].append('成品');base.write(p,'项目决策卡.json',c)
    (p/'试样.html').write_text('<html lang="zh-CN"><body>合成教学：城中有院，日常从容。</body></html>')
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="500" height="300"><rect x="20" y="20" width="450" height="250" fill="#abd"/><text x="40" y="80">合成教学</text></svg>'
    (p/'示意.svg').write_text(svg)
    base.write(p,'成品验收.json',{'文件':'试样.html','格式':'HTML','SHA256':digest(p/'试样.html'),'审阅人':'测试程序','状态':'通过',
        '逐项检查':{x:'通过' for x in ['文字与事实','溢出遮挡','阅读顺序','图表口径','内容去AI','页面去AI']},'总页数':1,
        '页面':[{'页码':1,'截图':'示意.svg','SHA256':digest(p/'示意.svg'),'可见问题':'隔离字段测试，不是页面实审'}]})
    base.write(p,'页面内容记录.json',{'成品SHA256':digest(p/'试样.html'),
        '素材':[{'ID':'A1','类型':'关系示意','来源性质':'合成教学','来源说明':'隔离数据','文件':'示意.svg','SHA256':digest(p/'示意.svg'),'证据ID':['E1']}],
        '页面':[{'页码':1,'标题':'归家路径','核心判断':'联系街区与内院','正文要点':['合成关系说明'],'视觉责任':'关系解释','素材ID':['A1'],'证据ID':['E1'],'图文作用':'解释空间联系','复核意见':'测试数据，无实际视觉结论'}]})

class StoryRegression(unittest.TestCase):
    def setUp(self):self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name);fixture(self.p)
    def tearDown(self):self.t.cleanup()
    def audit(self):return base.audit.audit(self.p)
    def mutate(self,n,fn):v=read(self.p,n);fn(v);base.write(self.p,n,v)
    def test_complete_conditional_story_accepted(self):self.assertEqual(self.audit()['机器检查'],'通过')
    def test_responsibility_required(self):
        self.mutate('项目决策卡.json',lambda v:v.pop('交付责任'));self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_complete_story_cannot_submit_value_only(self):
        self.mutate('项目决策卡.json',lambda v:v.update({'需输出模块':['价值']}));(self.p/'故事线底稿.json').unlink();self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_missing_chapter_rejected(self):
        self.mutate('故事线底稿.json',lambda v:v.update({'章节':[]}));self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_missing_extension_rejected(self):
        self.mutate('故事线底稿.json',lambda v:v.update({'传播延展':[]}));self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_unrelated_feature_rejected(self):
        self.mutate('故事线底稿.json',lambda v:v['主题方向'][0].update({'特征ID':['absent']}));self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_chapter_theme_mismatch(self):
        self.mutate('故事线底稿.json',lambda v:v['章节'][0].update({'主题ID':'other'}));self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_main_value_must_exist(self):
        self.mutate('价值决策底稿.json',lambda v:v['卖点取舍'].update({'主卖点ID':'absent'}));self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_duplicate_ids_rejected(self):
        self.mutate('故事线底稿.json',lambda v:v['主题方向'].append(dict(v['主题方向'][0])));self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_specialist_not_forced_full_story(self):
        self.mutate('项目决策卡.json',lambda v:v.update({'交付责任':['专项建议'],'需输出模块':['价值']}));(self.p/'故事线底稿.json').unlink();self.assertEqual(self.audit()['机器检查'],'通过')
    def test_graphic_records_accepted_as_records_only(self):graphic(self.p);self.assertEqual(self.audit()['机器检查'],'通过')
    def test_graphic_missing_asset_rejected(self):
        graphic(self.p);self.mutate('页面内容记录.json',lambda v:v['页面'][0].update({'素材ID':[]}));self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_graphic_stale_file_rejected(self):
        graphic(self.p);self.mutate('页面内容记录.json',lambda v:v.update({'成品SHA256':'outdated'}));self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_graphic_page_count_rejected(self):
        graphic(self.p);self.mutate('页面内容记录.json',lambda v:v.update({'页面':[]}));self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_decoration_cannot_be_evidence(self):
        graphic(self.p);self.mutate('页面内容记录.json',lambda v:(v['页面'][0].update({'视觉责任':'事实证据'}),v['素材'][0].update({'类型':'概念图'})));self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_expression_required_in_112(self):
        (self.p/'表达验收.json').unlink();self.assertEqual(self.audit()['机器检查'],'未通过')

if __name__=='__main__':unittest.main(verbosity=2)
