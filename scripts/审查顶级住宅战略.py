#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审查顶级/超高端住宅是否从普通改善升级为稀缺资源与控制权逻辑。"""
import argparse
import json
import sys
from pathlib import Path

必需字段 = [
    "项目级别与触发依据", "购买角色卡", "客户资产与决策结构", "多居所/资产组合角色",
    "一票否决", "不可替代资源账本", "推荐控制权", "控制权到产品机制",
    "服务治理", "溢价分解", "风险折价", "反伪豪宅检查",
    "控制权文学跃迁", "撤回/降级信号",
]
控制权 = {"到达控制权", "隐私控制权", "空间控制权", "时间控制权", "社交控制权", "服务控制权", "资产控制权"}
空值 = {"", "-", "—", "待定", "TBD", "同上", "按项目确定"}


def 有效(v, n=8):
    if isinstance(v, (dict, list)):
        t = json.dumps(v, ensure_ascii=False)
    else:
        t = str(v or "")
    return len("".join(t.split())) >= n and t.strip() not in 空值


def 审查(d):
    失败 = []
    for k in 必需字段:
        if not 有效(d.get(k)):
            失败.append("缺少有效字段：" + k)

    角色 = d.get("购买角色卡")
    if not isinstance(角色, dict):
        失败.append("购买角色卡必须是对象")
    else:
        for k in ("决策主体", "本次购买角色", "资金来源", "持有周期", "专业参与者", "使用与处置责任人"):
            if not 有效(角色.get(k), 4):
                失败.append("购买角色卡缺少：" + k)

    资源 = d.get("不可替代资源账本")
    if not isinstance(资源, list) or len(资源) < 3:
        失败.append("不可替代资源少于3项")
    else:
        for i, x in enumerate(资源, 1):
            if not isinstance(x, dict):
                失败.append(f"资源{i}不是对象")
                continue
            for k in ("资源事实", "数量/边界", "确定性", "客户使用时刻", "竞品与可复制性", "转化控制权"):
                if not 有效(x.get(k), 4):
                    失败.append(f"资源{i}缺少：{k}")

    推荐 = d.get("推荐控制权")
    if not isinstance(推荐, list) or not (3 <= len(推荐) <= 5):
        失败.append("推荐控制权应为3—5项，避免缺失或全量堆砌")
    elif any(x not in 控制权 for x in 推荐):
        失败.append("推荐控制权包含未定义类别")

    机制 = d.get("控制权到产品机制")
    if not isinstance(机制, list) or len(机制) < 5:
        失败.append("控制权到产品机制少于5项")
    else:
        for i, x in enumerate(机制, 1):
            if not isinstance(x, dict):
                失败.append(f"产品机制{i}不是对象")
                continue
            for k in ("控制权", "风险", "机制", "参数", "成本维护", "支付证明", "撤回信号"):
                if not 有效(x.get(k), 3):
                    失败.append(f"产品机制{i}缺少：{k}")

    服务 = d.get("服务治理")
    if isinstance(服务, dict):
        for k in ("运营主体", "SLA", "权限与隐私", "费用透明", "人员稳定", "替换/退出机制"):
            if not 有效(服务.get(k), 4):
                失败.append("服务治理缺少：" + k)
    else:
        失败.append("服务治理必须是对象")

    溢价 = d.get("溢价分解")
    if not isinstance(溢价, list) or len(溢价) < 4:
        失败.append("溢价分解少于4项")
    else:
        for i, x in enumerate(溢价, 1):
            if not isinstance(x, dict) or not all(有效(x.get(k), 3) for k in ("项目", "证据", "幅度区间", "反对理由", "失效信号")):
                失败.append(f"溢价分解{i}缺少证据、区间、反对理由或失效信号")

    反伪 = d.get("反伪豪宅检查")
    if not isinstance(反伪, dict) or any(v is not False for v in 反伪.values()):
        失败.append("反伪豪宅检查必须逐项明确为False；命中任一项即退回")

    跃迁 = d.get("控制权文学跃迁")
    if isinstance(跃迁, dict):
        for k in ("已有很多住所仍购买本案的理由", "独有控制权", "项目兑现机制", "关系改变", "5秒主张"):
            if not 有效(跃迁.get(k), 8):
                失败.append("控制权文学跃迁缺少：" + k)
    else:
        失败.append("控制权文学跃迁必须是对象")
    return list(dict.fromkeys(失败))


def 自检():
    资源 = [{"资源事实": f"不可新增资源{i}", "数量/边界": "明确数量边界", "确定性": "规划法律已核验", "客户使用时刻": "真实到达使用时刻", "竞品与可复制性": "最强竞品无法复制", "转化控制权": "隐私控制权"} for i in range(3)]
    机制 = [{"控制权": "隐私控制权", "风险": "混杂客流暴露", "机制": "独立门厅与权限分流", "参数": "单元与动线参数", "成本维护": "成本及长期维护", "支付证明": "客户尽调与价敏", "撤回信号": "不愿付费则撤回"} for _ in range(5)]
    溢价 = [{"项目": f"溢价项{i}", "证据": "竞品成交与客户样本", "幅度区间": "区间待实证校准", "反对理由": "可能被未来供给复制", "失效信号": "竞品快速复制时失效"} for i in range(4)]
    d = {k: "包含项目专属证据与边界" for k in 必需字段}
    d.update({
        "购买角色卡": {k: "具体且可核验" for k in ("决策主体", "本次购买角色", "资金来源", "持有周期", "专业参与者", "使用与处置责任人")},
        "不可替代资源账本": 资源,
        "推荐控制权": ["到达控制权", "隐私控制权", "资产控制权"],
        "控制权到产品机制": 机制,
        "服务治理": {k: "明确可执行标准" for k in ("运营主体", "SLA", "权限与隐私", "费用透明", "人员稳定", "替换/退出机制")},
        "溢价分解": 溢价,
        "反伪豪宅检查": {"配套数量替代稀缺": False, "公开圈层削弱隐私": False, "共享酒店客流未隔离": False, "服务无治理": False},
        "控制权文学跃迁": {k: "绑定独有资源、控制权与人物关系变化" for k in ("已有很多住所仍购买本案的理由", "独有控制权", "项目兑现机制", "关系改变", "5秒主张")},
    })
    if 审查(d):
        print("顶级住宅战略自检：合格样本被误拒")
        return 1
    d["推荐控制权"] = list(控制权)
    if not 审查(d):
        print("顶级住宅战略自检：全量堆砌未被拒绝")
        return 1
    print("顶级住宅战略自检：通过；可拦截普通改善放大、资源无边界、控制权堆砌和服务无治理。")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("底稿", type=Path, nargs="?")
    p.add_argument("--自检", action="store_true")
    a = p.parse_args()
    if a.自检:
        return 自检()
    if not a.底稿:
        p.error("必须提供底稿或使用--自检")
    try:
        d = json.loads(a.底稿.read_text(encoding="utf-8"))
    except Exception as e:
        print("顶级住宅战略审查：无法读取：", e)
        return 2
    失败 = 审查(d)
    if 失败:
        print("顶级住宅战略审查：未通过")
        for x in 失败:
            print("- " + x)
        return 1
    print("顶级住宅战略审查：通过；购买角色、不可替代资源、控制权、服务治理、溢价与概念跃迁完整。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
