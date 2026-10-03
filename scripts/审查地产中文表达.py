#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查方法、脚本和对外表达是否使用同一套地产中文。"""
import argparse
import re
import sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
说明文件 = 根 / "references" / "地产行业中文表达与案例启发.md"

生硬术语 = [
    "品类旧答案", "项目昂贵选择", "双重束缚", "竞品迁移测试", "战略创意简报",
    "信息充分性与降级交付", "客户方向性盲测", "通用态度警戒", "深描执行包",
    "信念障碍", "客户状态", "英雄动作", "创意机制", "单一命题", "语言人格",
    "相信理由", "客户转变", "新评判标准", "价值证据单元", "战役板", "归因口径",
]
英文框架词 = re.compile(
    r"\b(category old answer|expensive choice|double bind|hero action|"
    r"brand proposition|reason to believe|salience)\b",
    re.I,
)
扫描后缀 = {".md", ".json", ".py", ".yaml", ".yml"}


def 扫描文件(路径):
    try:
        内容 = 路径.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    问题 = []
    for 行号, 行 in enumerate(内容.splitlines(), 1):
        for 词 in 生硬术语:
            if 词 in 行:
                问题.append((路径, 行号, f"生硬术语：{词}"))
        命中 = 英文框架词.search(行)
        if 命中:
            问题.append((路径, 行号, f"未消化的英文框架词：{命中.group(0)}"))
    return 问题


def 收集(目标):
    if 目标.is_file():
        return [目标]
    return [
        p for p in 目标.rglob("*")
        if p.is_file()
        and p.suffix.lower() in 扫描后缀
        and p.resolve() not in {说明文件.resolve(), Path(__file__).resolve()}
    ]


def 主程序():
    解析 = argparse.ArgumentParser()
    解析.add_argument("目标", type=Path, nargs="?", default=根)
    解析.add_argument("--自检", action="store_true")
    参数 = 解析.parse_args()

    if 参数.自检:
        好 = "项目取舍、两难困境、概念推导底稿、换盘测试、概念初测。"
        坏 = "先写项目昂贵选择，再做双重束缚和竞品迁移测试。"
        if any(词 in 好 for 词 in 生硬术语) or not any(词 in 坏 for 词 in 生硬术语):
            print("地产中文表达自检：测试样本失效")
            return 1

    问题 = []
    for 文件 in 收集(参数.目标.resolve()):
        问题.extend(扫描文件(文件))
    if 问题:
        print("地产中文表达审查：未通过")
        for 文件, 行号, 原因 in 问题:
            try:
                相对 = 文件.relative_to(根)
            except ValueError:
                相对 = 文件
            print(f"- {相对}:{行号}｜{原因}")
        return 1
    print("地产中文表达审查：通过；方法、脚本与对外表达使用同一套地产中文。")
    return 0


if __name__ == "__main__":
    sys.exit(主程序())
