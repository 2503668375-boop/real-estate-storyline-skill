#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拦截HTML空页、废页、重复页、套话短页与明显中国语境表达风险。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
规则 = json.loads((根 / "references" / "统一规则.json").read_text(encoding="utf-8"))


class 页面解析器(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.页面 = []
        self.当前 = None
        self.深度 = 0
        self.忽略 = 0

    def handle_starttag(self, tag, attrs):
        属性 = dict(attrs)
        类名 = set((属性.get("class") or "").split())
        空元素 = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
        if self.当前 is None and 规则["HTML页面类"] in 类名:
            self.当前 = {
                "id": 属性.get("id") or f"第{len(self.页面) + 1}页",
                "原型": (属性.get("data-prototype") or "").strip(),
                "文本片段": [],
                "视觉": 0,
            }
            self.深度 = 1
        elif self.当前 is not None and tag not in 空元素:
            self.深度 += 1
        if tag in {"script", "style", "noscript"}:
            self.忽略 += 1
        if self.当前 is not None:
            if tag in {"img", "svg", "canvas", "video", "picture"} or "data-visual" in 属性:
                self.当前["视觉"] += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.忽略:
            self.忽略 -= 1
        if self.当前 is not None:
            self.深度 -= 1
            if self.深度 == 0:
                self.页面.append(self.当前)
                self.当前 = None

    def handle_data(self, data):
        if self.当前 is not None and not self.忽略:
            片段 = re.sub(r"\s+", " ", data).strip()
            if 片段:
                self.当前["文本片段"].append(片段)


def 规范文本(文本):
    文本 = re.sub(r"上一页|下一页|返回目录|目录|\d+\s*/\s*\d+", "", 文本)
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9%]+", "", 文本).lower()


def 去通用词(文本):
    结果 = 文本
    for 词 in 规则["低信息通用词"]:
        结果 = 结果.replace(规范文本(词), "")
    return 结果


def main():
    命令 = argparse.ArgumentParser()
    命令.add_argument("HTML", type=Path)
    命令.add_argument("--严格表达", action="store_true", help="把明显翻译腔风险升级为硬失败")
    参数 = 命令.parse_args()
    try:
        源码 = 参数.HTML.read_text(encoding="utf-8", errors="strict")
    except Exception as 错误:
        print("页面有效性审查：无法读取HTML：" + str(错误))
        return 2

    解析 = 页面解析器()
    解析.feed(源码)
    页面 = 解析.页面
    失败, 警告 = [], []
    阈值 = 规则["页面有效性"]
    低字数原型 = set(规则["低字数页面原型"])
    if not 页面:
        失败.append("没有发现静态slide页面")

    规范页 = []
    for 序号, 页 in enumerate(页面, 1):
        原文 = " ".join(页["文本片段"])
        文本 = 规范文本(原文)
        规范页.append(文本)
        名称 = f"第{序号}页({页['id']})"
        低字数页 = 页["原型"] in 低字数原型
        最少 = 阈值["封面章节最少有效字符"] if 低字数页 else 阈值["普通页最少有效字符"]
        if len(文本) < 最少:
            失败.append(f"{名称}有效文字仅{len(文本)}字，疑似空页或装饰页")
        if not 低字数页 and len(页["文本片段"]) <= 2 and len(文本) < 50:
            失败.append(f"{名称}几乎只有标题或标题同义改写")
        通用命中 = [词 for 词 in 规则["低信息通用词"] if 词 in 原文]
        实义 = 去通用词(文本)
        if len(文本) < 80 and len(通用命中) >= 2 and len(实义) < 阈值["套话短页最少实义字符"]:
            失败.append(f"{名称}主要由通用价值词构成：" + "、".join(通用命中[:6]))
        if not 低字数页 and 页["视觉"] == 0 and len(文本) < 70:
            警告.append(f"{名称}文字较少且没有可识别视觉证据，需人工核对页面任务")
        风险 = [词 for 词 in 规则["翻译腔风险表达"] if 词 in 原文]
        if 风险:
            消息 = f"{名称}命中明显翻译腔风险：" + "、".join(风险)
            (失败 if 参数.严格表达 else 警告).append(消息)

    for i in range(len(规范页)):
        if len(规范页[i]) < 20:
            continue
        for j in range(i + 1, len(规范页)):
            if len(规范页[j]) < 20:
                continue
            相似度 = SequenceMatcher(None, 规范页[i], 规范页[j]).ratio()
            if 相似度 >= 阈值["重复相似度"]:
                失败.append(f"第{i + 1}页与第{j + 1}页内容相似度{相似度:.0%}，疑似重复凑页")

    print(f"中国语境与页面有效性审查：静态页{len(页面)}；硬失败{len(dict.fromkeys(失败))}；提醒{len(dict.fromkeys(警告))}")
    if 失败:
        print("\n硬失败：")
        for 项 in dict.fromkeys(失败):
            print("- " + 项)
    if 警告:
        print("\n人工复核提醒：")
        for 项 in dict.fromkeys(警告):
            print("- " + 项)
    if not 失败:
        print("\n自动底线通过；仍须按《中国语境与逻辑文学双核》逐页人工审核因果、边界、文学准确性与合并测试。")
    return 1 if 失败 else 0


if __name__ == "__main__":
    sys.exit(main())
