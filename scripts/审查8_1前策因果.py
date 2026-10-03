#!/usr/bin/env python3
"""审查 8.1 前策决策链是否按上游事实向下游方案正向推进。"""

import argparse
import json
import sys
from pathlib import Path


ORDER = [
    "外部趋势",
    "城市板块",
    "土地能力",
    "消费阶层",
    "生活行为",
    "产品机会",
    "产品战略",
    "设计任务",
    "经营价格",
    "项目定位",
    "核心概念",
    "推广案名",
    "传播营销",
]


def text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False)


def sample():
    nodes = []
    for index, name in enumerate(ORDER, 1):
        nodes.append(
            {
                "ID": f"N{index:02d}",
                "节点": name,
                "上游输入": ["项目原始资料"] if index == 1 else [f"N{index-1:02d}"],
                "证据状态": "已核验事实与项目组判断分列",
                "本节点判断": f"{name}形成一项明确、可证伪且带时限的项目判断",
                "排除选项": "排除与上游证据冲突的惯性方案",
                "下游决定": "改变下一节点的面积、价格、配置或传播决定",
                "量化后果": "记录面积、套数、总价、成本、时间或转化指标",
                "最大不确定性": "样本、政策或工程边界仍需下一轮校准",
                "撤回信号": "出现相反成交、客户或工程证据时撤回并回退",
            }
        )
    return {
        "版本": "9.0",
        "趋势结论": {
            "时间范围": "未来12个月",
            "方向": "结构性分化并由优质产品率先修复",
            "分化对象": ["核心/外围", "新房/二手", "刚需/改善"],
            "产品后果": ["识别决策分叉并生成产品情境", "调整主力总价", "分批供货"],
            "失效信号": ["库存反转", "价格反转", "改善去化反转"],
            "观察源": ["官方数据", "J.P. Morgan", "趋势动物", "冰山指数"],
        },
        "情境数量说明": "情境由支付边界与低密土地能力如何分配这一真实分叉生成，不采用固定面积菜单",
        "决策分叉": [
            {
                "ID": "F01",
                "驱动变量": "改善需求修复、二手承接低总价需求、家庭置换支付边界与低密土地能力",
                "证据": "官方成交、竞品去化、客户访谈、总价敏感与土地测算交叉验证",
                "为何形成分叉": "土地可提高户均资源，但更高总价可能压缩有效客群，需要比较两种因果路径",
                "分支": ["P01", "P02"],
            }
        ],
        "产品情境": [
            {
                "ID": "P01", "来源分叉": ["F01"], "状态": "可行分支",
                "因果假设": "目标家庭愿为可感知的户均资源与代际功能支付",
                "目标客群": "具备稳定置换资金的成长家庭", "消费任务": "兼顾陪伴、独处、家务与长期成长",
                "竞品关系": "避开同质低总价存量，形成可支付的产品代际差", "土地能力": "把低密能力转为户均资源与私密",
                "面积套数配置": "由总价盲测、标准层效率和客户任务联算", "总价支付": "以资产出售、首付和月供三项验证",
                "货值成本现金流": "联算售价、套数、建安精装、货值、利润与现金流", "去化供货": "按有效客群规模分批供货",
                "停止条件": "总价接受或改善客群规模低于安全线",
            },
            {
                "ID": "P02", "来源分叉": ["F01"], "状态": "被排除反事实",
                "因果假设": "用更多套数和较低总价扩大需求池",
                "目标客群": "低总价优先的本地首置与刚改", "消费任务": "在有限总价内获得基本房间数",
                "竞品关系": "与二手和板块存量高度重叠", "土地能力": "把低密能力更多转为总价与套数效率",
                "面积套数配置": "由二手替代和标准层效率反算", "总价支付": "总价较低但需验证新房购买理由",
                "货值成本现金流": "测算套数增加是否抵消售价与竞争压力", "去化供货": "若采用则小批测试而非全盘预设",
                "停止条件": "新房代际差不足且被二手价格持续分流",
            },
        ],
        "消费行为接口": [
            {
                "行为": "使用全自动扫拖机器人",
                "设计接口": "基站柜体、给水、排水、防返水、插座、通风和检修",
                "参数": "按目标设备尺寸与换机兼容校核",
                "验证": "设备清单、入户访谈和机电评审",
            }
        ],
        "名称身份": {
            "项目定位": "服务目标阶层并占据明确市场角色的完整判断",
            "核心概念": "由产品与经营选择压缩出的思想命题",
            "推广案名": "完成语音、文化、重名和商标核验的识别名称",
            "Slogan": "阶段传播句",
        },
        "节点": nodes,
    }


def validate(data):
    failures = []
    if text(data.get("版本")) != "9.0":
        failures.append("版本不是9.0")

    nodes = data.get("节点")
    if not isinstance(nodes, list):
        failures.append("缺少节点列表")
        nodes = []

    names = [text(node.get("节点")) for node in nodes if isinstance(node, dict)]
    for expected in ORDER:
        if expected not in names:
            failures.append(f"缺少因果节点：{expected}")
    positions = [names.index(name) for name in ORDER if name in names]
    if positions != sorted(positions):
        failures.append("节点顺序倒置；必须按趋势到传播正向推进")

    for index, node in enumerate(nodes, 1):
        if not isinstance(node, dict):
            failures.append(f"节点{index}不是对象")
            continue
        for key in (
            "ID",
            "节点",
            "上游输入",
            "证据状态",
            "本节点判断",
            "排除选项",
            "下游决定",
            "量化后果",
            "最大不确定性",
            "撤回信号",
        ):
            minimum = 2 if key == "ID" else 4
            if len(text(node.get(key))) < minimum:
                failures.append(f"节点{index}缺少有效字段：{key}")
        if index > 1:
            previous = nodes[index - 2]
            previous_id = text(previous.get("ID")) if isinstance(previous, dict) else ""
            if previous_id and previous_id not in text(node.get("上游输入")):
                failures.append(f"节点{index}未引用直接上游{previous_id}")

    trend = data.get("趋势结论")
    if not isinstance(trend, dict):
        failures.append("缺少趋势结论")
    else:
        for key in ("时间范围", "方向", "分化对象", "产品后果", "失效信号", "观察源"):
            if len(text(trend.get(key))) < 4:
                failures.append(f"趋势结论缺少：{key}")
        sources = text(trend.get("观察源")).lower()
        if "官方" not in sources:
            failures.append("趋势观察源缺少官方数据")
        if not any(name in sources for name in ("j.p. morgan", "jpmorgan", "摩根大通")):
            failures.append("趋势观察源缺少J.P. Morgan或等效宏观机构")
        if "趋势动物" not in sources:
            failures.append("趋势观察源缺少趋势动物或其不可用说明")
        if "冰山" not in sources:
            failures.append("趋势观察源缺少冰山指数或其不可用说明")

    if len(text(data.get("情境数量说明"))) < 12:
        failures.append("缺少情境数量与类型如何由证据生成的说明")

    forks = data.get("决策分叉")
    if not isinstance(forks, list) or not forks:
        failures.append("缺少由市场、消费、土地、竞品、支付或经营证据形成的决策分叉")
        forks = []
    fork_ids = set()
    branch_ids = set()
    for index, fork in enumerate(forks, 1):
        if not isinstance(fork, dict):
            failures.append(f"决策分叉{index}不是对象")
            continue
        for key in ("ID", "驱动变量", "证据", "为何形成分叉", "分支"):
            minimum = 2 if key == "ID" else 4
            if len(text(fork.get(key))) < minimum:
                failures.append(f"决策分叉{index}缺少：{key}")
        fork_id = text(fork.get("ID"))
        if fork_id in fork_ids:
            failures.append(f"决策分叉ID重复：{fork_id}")
        fork_ids.add(fork_id)
        branches = fork.get("分支")
        if not isinstance(branches, list) or len(branches) < 2:
            failures.append(f"决策分叉{index}少于两个可检验分支；若仅一条可行，仍须记录被排除反事实")
        else:
            branch_ids.update(text(x) for x in branches)

    scenarios = data.get("产品情境")
    if not isinstance(scenarios, list) or not scenarios:
        failures.append("缺少由决策分叉生成的产品情境")
        scenarios = []
    scenario_ids = set()
    for index, scenario in enumerate(scenarios, 1):
        if not isinstance(scenario, dict):
            failures.append(f"产品情境{index}不是对象")
            continue
        for key in (
            "ID", "来源分叉", "状态", "因果假设", "目标客群", "消费任务",
            "竞品关系", "土地能力", "面积套数配置", "总价支付",
            "货值成本现金流", "去化供货", "停止条件",
        ):
            minimum = 2 if key == "ID" else 3
            if len(text(scenario.get(key))) < minimum:
                failures.append(f"产品情境{index}缺少：{key}")
        scenario_id = text(scenario.get("ID"))
        if scenario_id in scenario_ids:
            failures.append(f"产品情境ID重复：{scenario_id}")
        scenario_ids.add(scenario_id)
        source_forks = scenario.get("来源分叉")
        if not isinstance(source_forks, list) or not source_forks:
            failures.append(f"产品情境{index}未引用来源分叉")
        else:
            unknown = [text(x) for x in source_forks if text(x) not in fork_ids]
            if unknown:
                failures.append(f"产品情境{index}引用未知分叉：{','.join(unknown)}")
    missing_branches = sorted(branch_ids - scenario_ids)
    if missing_branches:
        failures.append("决策分叉引用了不存在的产品情境：" + "、".join(missing_branches))

    interfaces = data.get("消费行为接口")
    if not isinstance(interfaces, list) or not interfaces:
        failures.append("缺少消费行为到设计接口")
    else:
        for index, item in enumerate(interfaces, 1):
            for key in ("行为", "设计接口", "参数", "验证"):
                if len(text(item.get(key))) < 4:
                    failures.append(f"消费行为接口{index}缺少：{key}")

    identities = data.get("名称身份")
    if not isinstance(identities, dict):
        failures.append("缺少名称身份")
    else:
        values = []
        for key in ("项目定位", "核心概念", "推广案名", "Slogan"):
            value = text(identities.get(key))
            if len(value) < 4:
                failures.append(f"名称身份缺少：{key}")
            values.append(value)
        if len(set(values)) != len(values):
            failures.append("项目定位、核心概念、推广案名或Slogan发生混用")

    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?")
    parser.add_argument("--生成示例", action="store_true")
    parser.add_argument("--自测", action="store_true")
    args = parser.parse_args()

    if args.生成示例:
        print(json.dumps(sample(), ensure_ascii=False, indent=2))
        return 0
    if args.自测:
        failures = validate(sample())
        if failures:
            print("8.1前策因果自测：未通过")
            for item in failures:
                print(f"- {item}")
            return 1
        print("8.1前策因果自测：通过")
        return 0
    if not args.path:
        parser.error("请提供前策决策链.json，或使用 --生成示例")

    path = Path(args.path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"无法读取：{exc}")
        return 2

    failures = validate(data)
    if failures:
        print("8.1前策因果审查：未通过")
        for item in failures:
            print(f"- {item}")
        return 1
    print("8.1前策因果审查：通过")
    print("已覆盖趋势、土地、阶层行为、决策分叉、证据生成的产品情境、设计任务、经营、定位、概念、案名与传播的正向因果。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
