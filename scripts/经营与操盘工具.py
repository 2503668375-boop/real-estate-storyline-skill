#!/usr/bin/env python3
"""11.0 月度库存/资金与增量情景计算。仅标准库；不替代会计税务核验。"""
import argparse
import json
import math
import re
from pathlib import Path

CASH_KEYS = (
    '客户入受限', '客户入可用', '受限退款', '可用退款', '监管拨付',
    '受限项目支出', '可用项目支出', '受限融资提款', '可用融资提款',
    '融资还本', '融资利息', '股东投入', '股东分配', '最低可用储备',
)


def number(obj, key, default=None):
    value = obj.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(key + '必须是有限数字，未知不能填0或空值')
    if value < 0:
        raise ValueError(key + '不得为负数')
    return float(value)


def count(obj, key):
    value = number(obj, key)
    if not value.is_integer():
        raise ValueError(key + '必须为整数套数')
    return int(value)


def month_index(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}', value):
        raise ValueError('月份必须为YYYY-MM')
    year, month = map(int, value.split('-'))
    if not 1 <= month <= 12 or year < 1900:
        raise ValueError('月份无效')
    return year * 12 + month


def npv(cashflows, rate):
    discount = 1 / (1 + rate)
    return sum(c * (discount ** i) for i, c in enumerate(cashflows))


def returns(cashflows, annual_discount):
    """仅单次符号变化给IRR；逐月等间隔，返回年化与指定折现率NPV。"""
    monthly = (1 + annual_discount) ** (1 / 12) - 1
    answer = {'NPV': round(npv(cashflows, monthly), 6), '年化IRR': None, '说明': ''}
    signs = [1 if x > 0 else -1 for x in cashflows if x != 0]
    changes = sum(a != b for a, b in zip(signs, signs[1:]))
    if changes != 1:
        answer['说明'] = '无唯一常规IRR：现金流符号变化次数为' + str(changes)
        return answer
    # 缩放折现值避免长序列和近-100%区间溢出。
    def scaled(rate):
        n = len(cashflows) - 1
        if rate < 0:
            return sum(c * ((1 + rate) ** (n-i)) for i, c in enumerate(cashflows))
        return npv(cashflows, rate)
    low, high = -0.999999, 1.0
    f_low = scaled(low)
    while scaled(low) * scaled(high) > 0 and high < 1024:
        high *= 2
    if f_low * scaled(high) > 0:
        answer['说明'] = '求解区间无根，仅报告NPV'
        return answer
    for _ in range(160):
        mid = (low + high) / 2
        f_mid = scaled(mid)
        if f_low * f_mid <= 0:
            high = mid
        else:
            low, f_low = mid, f_mid
    annual = (1 + (low + high) / 2) ** 12 - 1
    answer['年化IRR'] = annual
    answer['说明'] = '按等间隔月度现金流求解，未自动加入期末残值'
    return answer


def calculate(data):
    if data.get('版本') != '11.0' or data.get('金额单位') != '万元':
        raise ValueError('版本须为11.0，金额单位须为万元')
    rate = number(data, '年折现率')
    scenarios = data.get('情景')
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError('缺少情景列表')
    output, names = [], set()
    for sc in scenarios:
        name = sc.get('名称')
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError('情景名称为空或重复')
        names.add(name)
        start = sc['期初']
        restricted = number(start, '受限现金')
        available = number(start, '可用现金')
        debt = number(start, '融资余额')
        stock = count(start, '可售库存')
        equity_cf = [-number(start, '股东投入占用')]
        rows, previous, min_cash, gap, flags = [], None, available, 0.0, []
        total_receipts = total_refunds = total_signed = total_cancel = 0.0
        periods = sc.get('月份')
        if not isinstance(periods, list) or not periods:
            raise ValueError(name + '缺少月份')
        deposit = sc.get('现售定金')
        deposit_balance, deposit_rows, release_month = 0.0, {}, None
        if deposit is not None:
            if not isinstance(deposit,dict): raise ValueError('现售定金须为对象')
            deposit_balance = number(deposit,'期初余额')
            if deposit_balance > restricted+1e-6: raise ValueError('期初受限定金超过受限现金')
            if deposit.get('解除监管最早月份') is not None:
                release_month = month_index(deposit['解除监管最早月份'])
            for entry in deposit.get('月度',[]):
                key = month_index(entry.get('月份'))
                if key in deposit_rows: raise ValueError('定金月份重复')
                deposit_rows[key] = {k:number(entry,k) for k in ['收取','退款','解除监管']}
            period_keys={month_index(m.get('月份')) for m in periods}
            if not set(deposit_rows).issubset(period_keys): raise ValueError('定金月份未对应现金模型')
        for month in periods:
            idx = month_index(month.get('月份'))
            if previous is not None and idx != previous + 1:
                raise ValueError(name + '月份须连续且不可重复')
            previous = idx
            default = 0 if month.get('缺省现金项为零') is True else None
            c = {k: number(month, k, default) for k in CASH_KEYS}
            if deposit is not None:
                dep = deposit_rows.get(idx,{'收取':0,'退款':0,'解除监管':0})
                if dep['解除监管']>0 and (release_month is None or idx<release_month):
                    raise ValueError('未达到已确认解除监管月份，不得释放现售定金')
                if dep['收取']>c['客户入受限']+1e-6 or dep['退款']>c['受限退款']+1e-6 or dep['解除监管']>c['监管拨付']+1e-6:
                    raise ValueError('定金明细未完整计入对应受限现金项')
                deposit_balance += dep['收取']-dep['退款']-dep['解除监管']
                if deposit_balance < -1e-6: raise ValueError('定金退款或解除超过余额')
            supplied = count(month, '新增可售')
            signed = count(month, '新增签约')
            canceled = count(month, '退订回补')
            locked = count(month, '转不可售')
            stock += supplied + canceled - signed - locked
            if stock < 0:
                raise ValueError(name + '库存为负，检查净签约及房源状态')
            restricted += c['客户入受限'] + c['受限融资提款'] - c['受限退款'] - c['监管拨付'] - c['受限项目支出']
            available += (c['客户入可用'] + c['监管拨付'] + c['可用融资提款'] + c['股东投入']
                          - c['可用退款'] - c['可用项目支出'] - c['融资还本'] - c['融资利息'] - c['股东分配'])
            debt += c['受限融资提款'] + c['可用融资提款'] - c['融资还本']
            if debt < -1e-6:
                raise ValueError(name + '融资还本超过余额')
            monthly_gap = max(0, c['最低可用储备'] - available)
            gap = max(gap, monthly_gap)
            if restricted < -1e-6:
                flags.append(month['月份'] + '受限账户不足，拨付或支出缺来源')
            if deposit is not None and restricted < deposit_balance-1e-6:
                flags.append(month['月份']+'受限现金不足以覆盖仍受监管的定金，不能将其用于自由支出')
            if monthly_gap > 1e-6:
                flags.append(month['月份'] + '可用现金低于储备')
            equity_cf.append(c['股东分配'] - c['股东投入'])
            total_receipts += c['客户入受限'] + c['客户入可用']
            total_refunds += c['受限退款'] + c['可用退款']
            total_signed += signed
            total_cancel += canceled
            min_cash = min(min_cash, available)
            rows.append({'月份': month['月份'], '期末可售': stock, '期末受限现金': round(restricted, 6),
                         '期末可用现金': round(available, 6), '期末总现金': round(restricted+available, 6),
                         '融资余额': round(debt, 6), '当月储备缺口': round(monthly_gap, 6)})
            if deposit is not None: rows[-1]['其中受限定金']=round(deposit_balance,6)
        result = {'名称': name, '月份': rows, '净签约套数': int(total_signed-total_cancel),
                  '实收净回款': round(total_receipts-total_refunds, 6), '最低可用现金': round(min_cash, 6),
                  '最大储备缺口': round(gap, 6), '资金可行': not flags, '资金警报': flags,
                  '股东现金流': equity_cf, '股东回报': returns(equity_cf, rate)}
        if '全投资现金流' in sc:
            cf = sc['全投资现金流']
            if not isinstance(cf, list) or len(cf) != len(periods)+1 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in cf):
                raise ValueError('全投资现金流须含期初且与月度长度一致')
            if not sc.get('全投资口径说明'):
                raise ValueError('全投资现金流须说明税费及融资口径')
            result['全投资回报'] = returns(cf, rate)
            result['全投资口径说明'] = sc['全投资口径说明']
        if '损益' in sc:
            pl = sc['损益']
            fields = ['收入不含增值税','结转开发成本','销售及管理费用','财务费用','税金及附加','土地增值税','所得税']
            amounts = {k:number(pl,k) for k in fields}
            profit = amounts['收入不含增值税'] - sum(amounts[k] for k in fields[1:])
            declared = pl.get('申报净利润')
            if isinstance(declared,bool) or not isinstance(declared,(int,float)) or not math.isfinite(declared):
                raise ValueError('申报净利润须为有限数字，可为亏损负数')
            if abs(declared-profit)>1e-6:
                raise ValueError(name+'申报净利润与收入成本费用税费不勾稽')
            if not pl.get('口径说明'):
                raise ValueError('损益须说明期间、含税处理、收入确认及成本税费范围')
            revenue = amounts['收入不含增值税']
            result['损益勾稽'] = {'净利润':round(profit,6),'净利率':profit/revenue if revenue else None,
                                  '边界':'只核输入项算术；税率、计税依据、收入确认和分摊未由工具认证'}
        output.append(result)
    baseline = data.get('基准情景')
    if baseline not in names:
        raise ValueError('基准情景名称不存在')
    ref = next(s for s in output if s['名称']==baseline)
    for s in output:
        s['较基准净回款变化'] = round(s['实收净回款']-ref['实收净回款'], 6)
        s['较基准股东NPV变化'] = round(s['股东回报']['NPV']-ref['股东回报']['NPV'], 6)
    return {'版本':'11.0','金额单位':'万元','基准情景':baseline,'情景':output,
            '边界':'仅核算输入的库存及现金；税费、利润、全投资现金流来源和市场参数须另行复核。期末现金不自动视为可分红。'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('输入',type=Path); ap.add_argument('--输出',type=Path)
    a=ap.parse_args()
    try:
        result=calculate(json.loads(a.输入.read_text(encoding='utf-8')))
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print('未通过：'+str(exc)); return 1
    text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
    if a.输出:
        a.输出.write_text(text+'\n',encoding='utf-8')
        print('已计算：'+str(a.输出))
    else: print(text)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
