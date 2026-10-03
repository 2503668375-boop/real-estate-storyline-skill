#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拦截空泛定位、通用态度、刚需羞辱、无项目代价和伪造共鸣通过。"""
import argparse, json, re, sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
规则 = json.loads((根 / "references" / "统一规则.json").read_text(encoding="utf-8"))
底稿字段 = 规则["概念推导底稿字段"]
调性字段 = 规则["概念表达调性字段"]
测试字段 = 规则["概念共鸣测试字段"]
警戒词 = 规则["概念警戒词"]
万能正确句 = 规则.get("万能正确句", [])
文学字段 = 规则.get("文学跃迁字段", [])
四项硬审 = 规则.get("概念四项硬审", [])
定位边界字段 = 规则.get("定位边界字段", [])
核心字段 = ["核心判断", "客户真实处境", "两难困境", "市场现有方案", "新的比较标准", "项目取舍", "独有做法", "可信依据", "客户获得的改变", "30秒复述", "表达调性", "带出的实际动作", "不成立条件"]
空话 = {"待定", "待核实", "TBD", "-", "—", "无", "同上", "按项目确定", "根据情况"}
万能结构 = (
    re.compile(r"每(?:个|一次|一步|一处|一种).{0,10}都"),
    re.compile(r"经得起(?:推敲|时间|检验|考验)"),
    re.compile(r"(?:让|为).{0,8}(?:生活|美好|选择).{0,6}(?:更好|而来|值得)"),
)


def 文本(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return re.sub(r"\s+", "", str(v or ""))


def 有效(v, n=4):
    t = 文本(v).strip()
    return len(t) >= n and t not in 空话


def 是万能正确句(s):
    t = 文本(s)
    return any(文本(x) in t for x in 万能正确句) or any(p.search(t) for p in 万能结构)


def 审查(d):
    失败, 提示 = [], []
    定位 = d.get("项目定位")
    if not 有效(定位, 28):
        失败.append("项目定位过短或不成完整战略判断")
    要素 = d.get("定位要素") if isinstance(d.get("定位要素"), dict) else {}
    for k in ("目标人物", "购房情境", "市场角色/新的比较标准", "独有做法", "两难困境", "边界"):
        if not 有效(要素.get(k), 6):
            失败.append("定位缺少要素：" + k)
    边界 = d.get("定位边界校准") if isinstance(d.get("定位边界校准"), dict) else {}
    for k in 定位边界字段:
        n = 2 if k == "上游证据ID" else 6
        if not 有效(边界.get(k), n):
            失败.append("定位边界校准缺少：" + k)
    证据ID = 边界.get("上游证据ID")
    if not isinstance(证据ID, list) or len(证据ID) < 3:
        失败.append("定位边界校准的上游证据ID少于3项")

    底稿 = d.get("概念推导底稿") if isinstance(d.get("概念推导底稿"), dict) else {}
    for k in 底稿字段:
        if not 有效(底稿.get(k), 6):
            失败.append("概念推导底稿缺少：" + k)
    if len(底稿.get("可信依据", [])) < 3 if isinstance(底稿.get("可信依据"), list) else True:
        失败.append("概念推导底稿的可信依据少于3条")

    概念 = d.get("核心概念") if isinstance(d.get("核心概念"), dict) else {}
    for k in 核心字段:
        if not 有效(概念.get(k), 6):
            失败.append("核心概念卡缺少：" + k)
    命题 = 文本(概念.get("核心判断"))
    if 命题 == "不将就的大盘":
        失败.append("命中失败回归样本：不将就的大盘")
    命中 = [x for x in 警戒词 if x in 命题]
    if 命中 and not 有效(概念.get("警戒词具体对象"), 8):
        失败.append("概念使用通用态度词但未明确具体对象：" + "、".join(命中))
    if 是万能正确句(命题):
        失败.append("核心判断命中万能正确句：只能作为企业态度，不能充当项目定位或核心概念")
    if len(概念.get("可信依据", [])) < 3 if isinstance(概念.get("可信依据"), list) else True:
        失败.append("核心概念可信依据少于3条")
    if len(概念.get("带出的实际动作", [])) < 5 if isinstance(概念.get("带出的实际动作"), list) else True:
        失败.append("概念生成的产品/价格/展示/销售/营销结果少于5项")

    调性 = 概念.get("表达调性") if isinstance(概念.get("表达调性"), dict) else {}
    for k in 调性字段:
        if not 有效(调性.get(k), 2):
            失败.append("表达调性缺少：" + k)
    跃迁 = d.get("文学跃迁卡") if isinstance(d.get("文学跃迁卡"), dict) else {}
    for k in 文学字段:
        n = 100 if k == "概念长文" else 20 if k in {"30秒人物讲法", "最后一跳"} else 6
        if not 有效(跃迁.get(k), n):
            失败.append("文学跃迁卡缺少有效字段：" + k)
    上游 = 跃迁.get("上游事实ID")
    if not isinstance(上游, list) or len(上游) < 3:
        失败.append("文学跃迁卡的上游事实ID少于3项")
    if 文本(跃迁.get("改变后的动作")) == 文本(跃迁.get("动作与物件")):
        失败.append("文学跃迁前后动作完全相同，没有形成可感知改变")
    if 是万能正确句(跃迁.get("5秒主张")):
        失败.append("文学跃迁的5秒主张仍是万能正确句")

    硬审 = d.get("概念四项硬审") if isinstance(d.get("概念四项硬审"), dict) else {}
    for k in 四项硬审:
        x = 硬审.get(k)
        if not isinstance(x, dict):
            失败.append("概念四项硬审缺少：" + k)
            continue
        if x.get("结论") != "通过":
            失败.append("概念四项硬审未通过：" + k)
        if not 有效(x.get("证据"), 12) or not 有效(x.get("最强反对理由"), 8):
            失败.append("概念四项硬审缺少证据或最强反对理由：" + k)

    终审 = d.get("独立创意终审") if isinstance(d.get("独立创意终审"), dict) else {}
    if 终审.get("是否与生成者独立") is not True:
        失败.append("缺少真正独立于生成者的创意终审")
    if 终审.get("结论") != "通过":
        失败.append("独立创意终审未通过；状态只能是结构通过、待独立创意终审")
    for k in ("评审人/代理", "最强反对理由", "最像的竞品或套话", "删改建议"):
        if not 有效(终审.get(k), 4):
            失败.append("独立创意终审缺少：" + k)
    迁移 = d.get("换盘测试")
    if not isinstance(迁移, list) or len(迁移) < 2:
        失败.append("换盘测试少于2个直接竞品")
    elif any(x.get("自然成立") is True for x in 迁移 if isinstance(x, dict)):
        失败.append("概念换给直接竞品仍自然成立")

    盲测 = d.get("概念初测") if isinstance(d.get("概念初测"), dict) else {}
    状态 = 文本(盲测.get("状态"))
    样本 = 盲测.get("样本") if isinstance(盲测.get("样本"), list) else []
    交付状态 = 文本(d.get("概念状态"))
    if 状态 != "已完成":
        if 交付状态 == "最终通过":
            失败.append("未完成真实客户盲测却宣称最终通过")
        else:
            提示.append("客户盲测未完成：概念只能标注方向待验证")
    else:
        目标 = [x for x in 样本 if isinstance(x, dict) and 文本(x.get("样本类型")) == "目标客户"]
        一线 = [x for x in 样本 if isinstance(x, dict) and 文本(x.get("样本类型")) in {"销售", "经纪"}]
        if len(目标) < 8:
            失败.append(f"目标客户盲测少于8人（实际{len(目标)}）")
        if len(一线) < 3:
            失败.append(f"销售/经纪一线盲测少于3人（实际{len(一线)}）")
        for i, x in enumerate(样本, 1):
            for k in 测试字段:
                if not 有效(x.get(k), 1):
                    失败.append(f"盲测样本{i}缺少：{k}")
        if 目标:
            def 比例(k): return sum(x.get(k) is True for x in 目标) / len(目标)
            if 比例("回述核心判断") < .70: 失败.append("目标客户正确回述率低于70%")
            if 比例("与我相关") < .60: 失败.append("目标客户相关率低于60%")
            if 比例("能指出可信依据") < .60: 失败.append("目标客户可信依据识别率低于60%")
            if 比例("愿进入下一步") < .50: 失败.append("目标客户下一步意向低于50%")
            if sum(x.get("被冒犯或被教育") is True for x in 目标) >= 2:
                失败.append("出现集中性的被冒犯/被教育反馈")

    return list(dict.fromkeys(失败)), 提示


def 样本():
    底稿 = {k: f"{k}包含本项目可核验的具体人物、动作、事实、取舍与边界" for k in 底稿字段}
    底稿["可信依据"] = ["图纸参数证据", "工程与成本证据", "客户行为证据"]
    调性 = {k: f"{k}有明确且单一的语言规则" for k in 调性字段}
    核心 = {k: f"{k}由购房情境、人物两难和项目独有做法正向推导" for k in 核心字段}
    核心["核心判断"] = "让有限总价仍能容纳家庭十年的变化"
    核心["可信依据"] = ["可变空间参数", "家务设备接口", "兑现时序制度"]
    核心["带出的实际动作"] = ["户型任务", "精装接口", "展示路径", "销售证据", "营销阶段动作"]
    核心["表达调性"] = 调性
    测试 = []
    for i in range(11):
        x = {k: f"{k}的逐字测试记录{i+1}" for k in 测试字段}
        x["样本类型"] = "目标客户" if i < 8 else "销售"
        x.update({"回述核心判断": True, "与我相关": i < 7, "能指出可信依据": i < 7, "愿进入下一步": i < 6, "被冒犯或被教育": False})
        测试.append(x)
    跃迁 = {k: f"{k}包含本项目人物、动作、摩擦、机制与新判断的完整推导" for k in 文学字段}
    跃迁["上游事实ID"] = ["M03", "C07", "P12"]
    跃迁["动作与物件"] = "下班后的夫妻把书包、外套和清洁设备同时推进入户收纳"
    跃迁["改变后的动作"] = "孩子先回到餐桌，父母不再为清洁动线互相让路"
    跃迁["概念长文"] = "这是一个完整的概念长文样本。它从下班回家的一次开门写起：书包、外套和清洁设备不再堵在同一条路上。项目用已经确定的空间与机电机制减少家务摩擦，让一家人先看见彼此，再处理生活。那条被重新腾出来的路，不只是动线，也是家庭在有限总价里仍能保留的从容与边界。"
    硬审 = {k: {"结论": "通过", "证据": f"{k}由三项本案事实和人物行为共同证明", "最强反对理由": f"{k}可能被竞品模仿但无法由其产品机制兑现"} for k in 四项硬审}
    return {
        "项目定位": "为受总价与家庭成长双重约束的首置家庭，在换房触发期提供可持续变化的日常居住系统，通过可变空间与设备接口解决面积有限和长期变化的两难，并拒绝用公区排场挤占户内有效投入。",
        "定位要素": {k: f"{k}包含具体项目判断" for k in ("目标人物", "购房情境", "市场角色/新的比较标准", "独有做法", "两难困境", "边界")},
        "定位边界校准": {
            "不服务谁": "不服务只追求会所排场且不在意户内效率的人",
            "不解决什么": "不承诺以有限总价覆盖全部豪宅配置",
            "不占据什么市场角色": "不占据泛改善或身份炫耀型市场角色",
            "最接近竞品及错位方式": "与竞品甲同总价，但把成本从低频公区错位到户内成长机制",
            "上游证据ID": ["M03", "C07", "P12"],
            "撤回信号": "目标家庭不重视长期变化且不愿为户内机制付费时撤回",
        },
        "概念推导底稿": 底稿, "核心概念": 核心,
        "文学跃迁卡": 跃迁,
        "概念四项硬审": 硬审,
        "独立创意终审": {
            "是否与生成者独立": True, "评审人/代理": "独立创意总监A",
            "最强反对理由": "仍可能被理解为常规可变户型，需要把家庭动作写得更锋利",
            "最像的竞品或套话": "类似成长住宅，但本案有设备接口与成本取舍证据",
            "删改建议": "删除抽象的持续二字，保留十年变化与具体动作",
            "结论": "通过",
        },
        "换盘测试": [{"竞品": "竞品甲", "自然成立": False}, {"竞品": "竞品乙", "自然成立": False}],
        "概念初测": {"状态": "已完成", "样本": 测试}, "概念状态": "最终通过"
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("底稿", type=Path, nargs="?")
    p.add_argument("--自检", action="store_true")
    a = p.parse_args()
    if a.自检:
        好 = 样本()
        if 审查(好)[0]:
            print("概念定位格调自检：合格样本被误拒")
            for x in 审查(好)[0]: print("- " + x)
            return 1
        坏 = json.loads(json.dumps(好, ensure_ascii=False))
        坏["核心概念"]["核心判断"] = "不将就的大盘"
        坏["核心概念"].pop("警戒词具体对象", None)
        if not any("不将就的大盘" in x for x in 审查(坏)[0]):
            print("概念定位格调自检：失败回归样本未被拒绝")
            return 1
        万能 = json.loads(json.dumps(好, ensure_ascii=False))
        万能["核心概念"]["核心判断"] = "每个选择都经得起推敲"
        万能["文学跃迁卡"]["5秒主张"] = "每个选择都经得起推敲"
        if not any("万能正确句" in x for x in 审查(万能)[0]):
            print("概念定位格调自检：万能正确句未被拒绝")
            return 1
        假 = json.loads(json.dumps(好, ensure_ascii=False))
        假["概念初测"] = {"状态": "未取得真实样本", "样本": []}
        if not any("宣称最终通过" in x for x in 审查(假)[0]):
            print("概念定位格调自检：伪造最终通过未被拒绝")
            return 1
        print("概念定位格调自检：合格样本通过；通用失败概念、万能正确句与伪造共鸣通过均被拒绝。")
        return 0
    if not a.底稿:
        p.error("必须提供底稿或使用--自检")
    try:
        d = json.loads(a.底稿.read_text(encoding="utf-8"))
    except Exception as e:
        print("概念定位格调审查：无法读取：", e)
        return 2
    失败, 提示 = 审查(d)
    for x in 提示: print("提示：", x)
    if 失败:
        print("概念定位格调审查：未通过")
        for x in 失败: print("- " + x)
        return 1
    print("概念定位格调审查：通过；定位、两难、项目取舍、表达调性、实际动作与共鸣验证完整。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
