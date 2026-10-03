#!/usr/bin/env python3
"""隔离回归：来源反例、现金守恒、库存与融资边界、价值证据与分项验收。"""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


cash=load('经营与操盘工具'); market=load('审查市场数据包'); audit=load('审查11版交付')


def model():
    return {'版本':'11.0','金额单位':'万元','年折现率':.12,'基准情景':'基准','情景':[{
        '名称':'基准','期初':{'受限现金':200,'可用现金':100,'融资余额':300,'可售库存':24,'股东投入占用':100},
        '月份':[{'月份':'2026-09','新增可售':0,'新增签约':2,'退订回补':0,'转不可售':0,
                 '缺省现金项为零':True,'客户入受限':400,'监管拨付':150,'受限项目支出':100,
                 '可用项目支出':200,'融资利息':3}]}]}


def write(folder,name,obj):
    (folder/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')


def value_fixture(folder):
    source='合成教学资料：仅达到交付标准，尚无额外支付证据。'
    (folder/'教学.txt').write_text(source,encoding='utf-8')
    write(folder,'证据台账.json',{'版本':'11.0','证据':[{'ID':'E1','主张':'仅达到交付标准','类型':'项目资料','状态':'估算',
        '日期':'2026-09-01','适用范围':'合成教学','来源文件':'教学.txt'}]})
    write(folder,'项目决策卡.json',{'版本':'11.0','项目':'合成教学','基准日':'2026-09-09','阶段':'现房尾盘',
        '本轮任务':'价值方向','目标优先级':['资金安全'],'可改项':['展示'],'锁定项':['结构'],
        '需输出模块':['价值'],'责任人与权限':'仅作研究，未获执行授权','决策状态':'探索'})
    v={'ID':'V1','主张':'可验证的基础居住条件','角色':'成交门槛','目标客户':'合成家庭','客户任务':'核实使用条件',
       '证据ID':['E1'],'可用机制':'实看与检测核对','竞争替代':'当地可比房源待核','客户代价':'暂无额外价格理由',
       '项目取舍':'先证明底线','成本兑现':'检测与展示成本待核','溢价状态':'不主张','表达方向':'可靠日常',
       '验证计划':'增加含价比较','失效条件':'检测不符合合同'}
    write(folder,'价值决策底稿.json',{'版本':'11.0','价值':[v]})
    return v


class Regression(unittest.TestCase):
    def test_cash_and_inventory(self):
        r=cash.calculate(model())['情景'][0]
        self.assertEqual(r['月份'][0]['期末总现金'],397)
        self.assertEqual(r['月份'][0]['期末可用现金'],47)
        self.assertEqual(r['月份'][0]['期末受限现金'],350)
        self.assertEqual(r['月份'][0]['期末可售'],22)
        self.assertEqual(r['股东回报']['年化IRR'],None)

    def test_transfer_not_new_money(self):
        a=model();b=copy.deepcopy(a)
        b['情景'][0]['月份'][0]['监管拨付']=180
        ar=cash.calculate(a)['情景'][0]['月份'][0];br=cash.calculate(b)['情景'][0]['月份'][0]
        self.assertEqual(ar['期末总现金'],br['期末总现金'])
        self.assertEqual(br['期末可用现金']-ar['期末可用现金'],30)

    def test_stock_and_overrepayment(self):
        for key,value in [('新增签约',25),('融资还本',301),('客户入可用',True),('客户入可用',float('nan'))]:
            m=model();m['情景'][0]['月份'][0][key]=value
            with self.assertRaises(ValueError): cash.calculate(m)

    def test_cash_gap_not_hidden(self):
        m=model();m['情景'][0]['月份'][0]['最低可用储备']=600
        r=cash.calculate(m)['情景'][0]
        self.assertFalse(r['资金可行']);self.assertEqual(r['最大储备缺口'],553)

    def test_discontinuous_months(self):
        m=model();row=copy.deepcopy(m['情景'][0]['月份'][0]);row['月份']='2026-11';m['情景'][0]['月份'].append(row)
        with self.assertRaises(ValueError):cash.calculate(m)

    def test_missing_not_zero(self):
        m=model();del m['情景'][0]['月份'][0]['缺省现金项为零']
        with self.assertRaises(ValueError):cash.calculate(m)

    def test_irr_and_ambiguity(self):
        r=cash.returns([-100]+[0]*11+[112],.12)
        self.assertAlmostEqual(r['年化IRR'],.12,places=8)
        self.assertAlmostEqual(r['NPV'],0,places=5)
        self.assertIsNone(cash.returns([-100,230,-132],.12)['年化IRR'])

    def test_original_market_counterexample_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'市场.json';rows=[]
            for i,dim in enumerate(sorted(market.DIMENSIONS)*2):
                rows.append({'证据ID':str(i),'维度':dim,'指标':'成交','数值':999,'单位':'套','统计期':'2099年13月',
                    '地域':'教学','口径':'教学','来源机构':'某机构','来源链接':'https://example.com/unverified',
                    '发布日期':'2099-99-99','抓取日期':'1900-01-01','证据级别':'机构原始报告',
                    '允许推断':'教学','对项目决定':'教学'})
            p.write_text(json.dumps({'版本':'11.0','项目':'教学','地域':'教学','统计截至':'2026-09-09','数据':rows}))
            bad=market.审查(p)
            self.assertTrue(any('占位' in x for x in bad));self.assertTrue(any('无效' in x for x in bad))

    def test_local_source_specialist_not_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);(folder/'成交.txt').write_text('合成示例：2026年8月本项目成交2套。')
            row={'证据ID':'M1','维度':'竞品成交','指标':'成交','数值':2,'单位':'套','统计期':'2026年8月',
                '地域':'教学','口径':'合成单项目','来源机构':'本地调查','来源文件':'成交.txt',
                '发布日期':'2026-09-01','抓取日期':'2026-09-09','证据级别':'教学估算','允许推断':'仅教学',
                '对项目决定':'演示专项结构'}
            write(folder,'市场.json',{'版本':'11.0','项目':'教学','地域':'教学','统计截至':'2026-09-09','用途':'专项','数据':[row]})
            self.assertEqual(market.审查(folder/'市场.json'),[])

    def test_value_only_and_unknown_id(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);v=value_fixture(folder)
            result=audit.audit(folder)
            self.assertEqual(result['机器检查'],'通过');self.assertTrue(result['提示'])
            v['证据ID']=['missing'];write(folder,'价值决策底稿.json',{'价值':[v]})
            self.assertEqual(audit.audit(folder)['机器检查'],'未通过')

    def test_premium_claim_requires_payment_proof(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);v=value_fixture(folder);v.update({'角色':'溢价理由','溢价状态':'有条件证据','选择证据':'自称有效','支付证据ID':'E1'})
            write(folder,'价值决策底稿.json',{'价值':[v]})
            self.assertTrue(any('溢价缺' in x for x in audit.audit(folder)['失败']))

    def test_source_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);value_fixture(folder)
            ledger=json.loads((folder/'证据台账.json').read_text())
            ledger['证据'][0].update({'状态':'已核验','核验人':'隔离测试程序','核验日':'2026-09-09',
                '原文摘录':'合成教学资料','SHA256':hashlib.sha256((folder/'教学.txt').read_bytes()).hexdigest()})
            write(folder,'证据台账.json',ledger)
            self.assertEqual(audit.audit(folder)['机器检查'],'通过')
            (folder/'教学.txt').write_text('被替换的数据')
            self.assertEqual(audit.audit(folder)['机器检查'],'未通过')

    def test_profit_reconciliation(self):
        m=model()
        pl={'收入不含增值税':1000,'结转开发成本':700,'销售及管理费用':50,'财务费用':20,
            '税金及附加':10,'土地增值税':30,'所得税':40,'申报净利润':150,'口径说明':'合成全周期损益'}
        m['情景'][0]['损益']=pl
        self.assertEqual(cash.calculate(m)['情景'][0]['损益勾稽']['净利润'],150)
        pl['申报净利润']=160
        with self.assertRaises(ValueError):cash.calculate(m)

    def test_policy_effective_date(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);v=value_fixture(folder)
            ledger=json.loads((folder/'证据台账.json').read_text())
            ledger['证据'][0]['生效日']='2026-09-20';write(folder,'证据台账.json',ledger)
            self.assertTrue(any('未生效' in x for x in audit.audit(folder)['失败']))
            v['适用日']='2026-10-01';write(folder,'价值决策底稿.json',{'价值':[v]})
            self.assertEqual(audit.audit(folder)['机器检查'],'通过')

    def test_land_requires_full_account(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);value_fixture(folder)
            card=json.loads((folder/'项目决策卡.json').read_text());card.update({'阶段':'拿地','需输出模块':['经营']})
            write(folder,'项目决策卡.json',card);write(folder,'经营价格底稿.json',model())
            self.assertTrue(any('全投资现金流' in x for x in audit.audit(folder)['失败']))

    def test_deposit_not_available_before_delivery(self):
        m=model();m['情景'][0]['现售定金']={'期初余额':0,'解除监管最早月份':'2027-03',
            '月度':[{'月份':'2026-09','收取':20,'退款':0,'解除监管':0}]}
        r=cash.calculate(m)['情景'][0]['月份'][0]
        self.assertEqual(r['其中受限定金'],20)
        self.assertEqual(r['期末总现金'],397)
        m['情景'][0]['现售定金']['月度'][0]['解除监管']=20
        with self.assertRaises(ValueError):cash.calculate(m)

    def test_deposit_cannot_fund_construction(self):
        m=model();row=m['情景'][0]['月份'][0]
        row.update({'客户入受限':20,'监管拨付':0,'受限项目支出':10})
        m['情景'][0]['期初']['受限现金']=0
        m['情景'][0]['现售定金']={'期初余额':0,'解除监管最早月份':None,
            '月度':[{'月份':'2026-09','收取':20,'退款':0,'解除监管':0}]}
        r=cash.calculate(m)['情景'][0]
        self.assertFalse(r['资金可行'])
        self.assertTrue(any('定金' in x for x in r['资金警报']))

    def test_expression_gate_and_current_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);value_fixture(folder)
            card=json.loads((folder/'项目决策卡.json').read_text());card['技能版本']='11.1';write(folder,'项目决策卡.json',card)
            self.assertEqual(audit.audit(folder)['机器检查'],'未通过')

            (folder/'稿件.md').write_text('合成试样：窗外那棵树，比我们更早住在这里。')
            record={'稿件文件':'稿件.md','SHA256':hashlib.sha256((folder/'稿件.md').read_bytes()).hexdigest(),
                '复核人':'测试夹具','复核类型':'作者自审','内容去AI':'通过','文学表达':'通过',
                '重点句':['窗外那棵树，比我们更早住在这里。'],'修改记录':'仅为隔离字段验证','复述记录':'合成记录，不是真实客研'}
            write(folder,'表达验收.json',record)
            self.assertEqual(audit.audit(folder)['机器检查'],'通过')
            (folder/'稿件.md').write_text('替换后的稿件')
            self.assertEqual(audit.audit(folder)['机器检查'],'未通过')

    def test_expression_html_visible_text(self):
        p=audit.VisibleText();p.feed('<style>隐藏</style><h1>树<span>影</span>在窗前</h1><script>假主张</script>')
        self.assertEqual(''.join(p.parts),'树影在窗前')


if __name__=='__main__':unittest.main(verbosity=2)
