#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从一个项目目录自动发现标准底稿，并串联全部关键审查。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
脚本 = 根 / "scripts"


def main():
    # 11.0 使用独立的分项验收；旧项目仍保留原格式入口。
    probe = argparse.ArgumentParser(add_help=False)
    probe.add_argument("--目录", type=Path, default=Path("."))
    known, _ = probe.parse_known_args()
    card = known.目录 / "项目决策卡.json"
    if card.exists():
        return subprocess.run([sys.executable, str(脚本 / "审查11版交付.py"), *sys.argv[1:]]).returncode
    p = argparse.ArgumentParser(description="9.0完整方案最终验收")
    p.add_argument("--目录", type=Path, default=Path("."))
    p.add_argument("--运行清单", type=Path)
    p.add_argument("--资料等级", type=Path)
    p.add_argument("--研究", type=Path)
    p.add_argument("--市场数据", type=Path)
    p.add_argument("--高端住宅", type=Path)
    p.add_argument("--前策", type=Path)
    p.add_argument("--价值", type=Path)
    p.add_argument("--文学", type=Path)
    p.add_argument("--概念", type=Path)
    p.add_argument("--创意终审", type=Path)
    p.add_argument("--营销", type=Path)
    p.add_argument("--HTML", type=Path)
    p.add_argument("--项目名")
    p.add_argument("--演示", action="store_true", help="演示版：跳过逐页截图视觉验收，强制标注演示状态")
    p.add_argument("--类型", choices=["完整"], default="完整")
    a = p.parse_args()

    目录 = a.目录.expanduser().resolve()

    def 取值(显式值: Path | None, 默认文件名: str) -> Path:
        if 显式值 is None:
            return 目录 / 默认文件名
        return 显式值.expanduser().resolve()

    a.运行清单 = 取值(a.运行清单, "项目运行清单.json")
    a.资料等级 = 取值(a.资料等级, "资料等级.json")
    a.研究 = 取值(a.研究, "研究底稿.json")
    a.市场数据 = 取值(a.市场数据, "市场数据包.json")
    a.前策 = 取值(a.前策, "前策决策链.json")
    a.价值 = 取值(a.价值, "价值推导底稿.json")
    a.文学 = 取值(a.文学, "文学主线底稿.json")
    a.概念 = 取值(a.概念, "概念与命名底稿.json")
    a.创意终审 = 取值(a.创意终审, "创意总监审查底稿.json")
    a.营销 = 取值(a.营销, "全周期营销底稿.json")
    a.HTML = 取值(a.HTML, "外部提案.html")
    a.页面事实 = 目录 / "页面事实清单.json"
    a.截图目录 = 目录 / "视觉验收" / "页图"
    a.项目名 = a.项目名 or 目录.name
    if a.高端住宅 is None:
        自动高端 = 目录 / "顶级住宅战略底稿.json"
        a.高端住宅 = 自动高端 if 自动高端.exists() else None
    else:
        a.高端住宅 = a.高端住宅.expanduser().resolve()

    必需文件 = [
        a.运行清单, a.资料等级, a.研究, a.市场数据, a.前策, a.价值, a.文学, a.概念,
        a.创意终审, a.营销, a.HTML, a.页面事实,
    ]
    缺失 = [str(x) for x in 必需文件 if not x.is_file()]
    if 缺失:
        print("完整方案最终验收：缺少标准文件")
        for 路径 in 缺失:
            print("- " + 路径)
        return 2

    命令 = [
        ("长任务运行清单", ["项目检查点.py", "verify", str(a.运行清单)]),
        ("资料等级", ["审查资料等级.py", str(a.资料等级)]),
        ("研究底稿", ["审查研究底稿.py", str(a.研究)]),
        ("市场数据包", ["审查市场数据包.py", str(a.市场数据)]),
        ("前策正向因果", ["审查8_1前策因果.py", str(a.前策)]),
        ("价值推导", ["审查价值推导链.py", str(a.价值), "--类型", "完整"]),
        ("文学主线", ["审查文学主线.py", str(a.文学)]),
        ("概念定位格调与文学跃迁", ["审查概念定位格调.py", str(a.概念)]),
        ("概念新颖性", ["审查概念新颖性.py", str(a.概念)]),
        ("独立创意终审", ["审查创意总监闸门.py", str(a.创意终审)]),
        ("全周期营销", ["审查全周期营销.py", str(a.营销)]),
        ("外部完整提案", ["审查外部完整提案.py", str(a.HTML), "--类型", "摘要" if a.演示 else "完整"]),
        ("HTML格式与运行", ["审查HTML汇报.py", str(a.HTML), "--类型", "摘要" if a.演示 else "完整", "--项目名", a.项目名]),
        ("内容实质与逐页视觉", ["审查内容实质.py", str(a.HTML), "--页面事实", str(a.页面事实), "--截图目录", str(a.截图目录)] + (["--演示"] if a.演示 else [])),
    ]
    if a.高端住宅:
        命令.insert(2, ("顶级住宅战略", ["审查顶级住宅战略.py", str(a.高端住宅)]))

    失败 = []
    for 名称, 参数 in 命令:
        print(f"\n===== {名称} =====")
        r = subprocess.run([sys.executable, str(脚本 / 参数[0]), *参数[1:]], text=True)
        if r.returncode != 0:
            失败.append(名称)

    print("\n===== 完整方案结论 =====")
    if 失败:
        print("完整方案最终验收：未通过")
        print("失败环节：" + "、".join(失败))
        print("不得向用户声称审查通过、完整方案或最终可交付。")
        return 1
    print("完整方案最终验收：全部通过")
    print("结构、文学跃迁、概念独立终审、外部模块完整性与HTML运行均已完成。")
    if a.演示:
        print("【演示版】已跳过逐页截图视觉验收；不得声称完整交付，仅结构通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
