#!/usr/bin/env python3
"""隔离测试正文、摘录、任务覆盖及旧版兼容；不测试审美或市场效果。"""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('story112',ROOT/'测试11_2故事线.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)


def read(p,n):return json.loads((p/n).read_text(encoding='utf-8'))
def write(p,n,v):(p/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def fixture(p):
    base.fixture(p)
    card=read(p,'项目决策卡.json');card['技能版本']='11.3';write(p,'项目决策卡.json',card)
    # 仅用于引用结构的合成文字；通过不代表这三句构成合格提案。
    text='合成教学：城中有院，日常从容。\n街道可达，院内声音尚未实测。\n便利与停留能否并存，需要比较穿行及声学条件。\n条件成立时优先组织归家路径，否则调整停留空间。\n'
    (p/'稿件.txt').write_text(text,encoding='utf-8')
    expression=read(p,'表达验收.json');expression['SHA256']=digest(p/'稿件.txt');write(p,'表达验收.json',expression)
    story=read(p,'故事线底稿.json');story['章节'][0]['论证ID']=['A1'];write(p,'故事线底稿.json',story)
    write(p,'论证展开审阅.json',{
        '稿件文件':'稿件.txt','SHA256':digest(p/'稿件.txt'),
        '复核人':'隔离测试程序','复核类型':'作者自审',
        '任务覆盖':[{'用户要求':'教学完整故事线结构','论证ID':['A1']}],
        '论证单元':[{'ID':'A1','问题':'如何组织便利与停留','章节ID':['C1'],'证据ID':['E1'],
            '原文摘录':{'事实与边界':'街道可达，院内声音尚未实测。',
                '解释与比较':'便利与停留能否并存，需要比较穿行及声学条件。',
                '项目决策':'条件成立时优先组织归家路径，否则调整停留空间。'},
            '审阅结论':'有条件展开','审阅意见':'仅演示三类摘录的正文关联，不评内容充分。',
            '条件与分叉':'声学满足再组织停留，否则调整位置。'}]})


class DepthRegression(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name);fixture(self.p)
    def tearDown(self):self.t.cleanup()
    def audit(self):return base.base.audit.audit(self.p)
    def mutate(self,n,fn):
        obj=read(self.p,n);fn(obj);write(self.p,n,obj)
    def rejected(self):
        self.assertEqual(self.audit()['机器检查'],'未通过')
    def test_record_pass_does_not_certify_depth(self):
        r=self.audit();self.assertEqual(r['机器检查'],'通过')
        self.assertEqual(r['分项']['内容深度评定']['状态'],'未自动评定')
    def test_missing_review(self):
        (self.p/'论证展开审阅.json').unlink();self.rejected()
    def test_missing_manuscript(self):
        (self.p/'稿件.txt').unlink();self.rejected()
    def test_stale_manuscript(self):
        (self.p/'稿件.txt').write_text('另一版正文');self.rejected()
    def test_excerpt_must_exist(self):
        self.mutate('论证展开审阅.json',lambda d:d['论证单元'][0]['原文摘录'].update({'项目决策':'正文没有写过'}));self.rejected()
    def test_blank_excerpt(self):
        self.mutate('论证展开审阅.json',lambda d:d['论证单元'][0]['原文摘录'].update({'事实与边界':' \n '}));self.rejected()
    def test_slogan_cannot_fill_all_roles(self):
        self.mutate('论证展开审阅.json',lambda d:d['论证单元'][0].update({'原文摘录':{k:'城中有院，日常从容。' for k in ['事实与边界','解释与比较','项目决策']}}));self.rejected()
    def test_missing_conditional_branch(self):
        self.mutate('论证展开审阅.json',lambda d:d['论证单元'][0].pop('条件与分叉'));self.rejected()
    def test_unexpanded_is_not_complete(self):
        self.mutate('论证展开审阅.json',lambda d:d['论证单元'][0].update({'审阅结论':'未展开'}));self.rejected()
    def test_chapter_without_argument(self):
        self.mutate('故事线底稿.json',lambda d:d['章节'][0].pop('论证ID'));self.rejected()
    def test_unknown_evidence(self):
        self.mutate('论证展开审阅.json',lambda d:d['论证单元'][0].update({'证据ID':['unknown']}));self.rejected()
    def test_unknown_argument(self):
        self.mutate('故事线底稿.json',lambda d:d['章节'][0].update({'论证ID':['unknown']}));self.rejected()
    def test_empty_task_coverage(self):
        self.mutate('论证展开审阅.json',lambda d:d.update({'任务覆盖':[]}));self.rejected()
    def test_inconsistent_expression_version(self):
        self.mutate('论证展开审阅.json',lambda d:d.update({'稿件文件':'copy.txt'}))
        (self.p/'copy.txt').write_bytes((self.p/'稿件.txt').read_bytes());self.rejected()
    def test_asymmetric_chapter_links(self):
        def add(d):
            c=copy.deepcopy(d['章节'][0]);c['ID']='C2';d['章节'].append(c)
        self.mutate('故事线底稿.json',add);self.rejected()
    def test_specialist_not_forced_full_story(self):
        self.mutate('项目决策卡.json',lambda d:d.update({'交付责任':['专项建议'],'需输出模块':['价值']}))
        (self.p/'论证展开审阅.json').unlink();(self.p/'故事线底稿.json').unlink()
        self.assertEqual(self.audit()['机器检查'],'通过')
    def test_112_compatibility(self):
        base.fixture(self.p);(self.p/'论证展开审阅.json').unlink()
        self.assertEqual(self.audit()['机器检查'],'通过')
    def test_unicode_whitespace_normalization(self):
        self.mutate('论证展开审阅.json',lambda d:d['论证单元'][0]['原文摘录'].update({'事实与边界':'街道可达，\n院内声音尚未实测。'}))
        self.assertEqual(self.audit()['机器检查'],'通过')
    def test_wrong_excerpt_object(self):
        self.mutate('论证展开审阅.json',lambda d:d['论证单元'][0].update({'原文摘录':[]}));self.rejected()
    def test_duplicate_argument_id(self):
        self.mutate('论证展开审阅.json',lambda d:d['论证单元'].append(copy.deepcopy(d['论证单元'][0])));self.rejected()


if __name__=='__main__':unittest.main(verbosity=2)
