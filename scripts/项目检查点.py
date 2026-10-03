#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为长方案维护可恢复、可校验的阶段运行清单。"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

默认阶段 = ["条件检查", "资料与研究", "市场/客群", "产品战略", "设计任务", "经营价格", "定位概念", "页面预算", "分批生成", "运行与视觉验收", "最终交付"]


def 时间():
    return datetime.now(timezone.utc).isoformat()


def 原子写(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def 摘要(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def 读取(path):
    return json.loads(path.read_text(encoding="utf-8"))


def 初始化(a):
    if a.清单.exists() and not a.覆盖:
        print("运行清单已存在；使用 status 或 verify，不覆盖已有进度。")
        return 1
    root = Path(a.正式目录).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print("正式目录不存在或不是目录：" + str(root))
        return 1
    if not os.access(root, os.W_OK):
        print("正式目录不可写：" + str(root))
        return 1
    stages = a.阶段 or 默认阶段
    d = {
        "schema_version": 1, "项目": a.项目, "正式目录": str(root), "最终成品": a.最终成品,
        "创建时间": 时间(), "更新时间": 时间(), "当前阶段": stages[0],
        "阶段": [{"名称": x, "状态": "in_progress" if i == 0 else "pending", "产物": [], "恢复说明": ""} for i, x in enumerate(stages)],
    }
    原子写(a.清单, d)
    print("已建立运行清单：" + str(a.清单))
    return 0


def 完成(a):
    d = 读取(a.清单)
    root = Path(d["正式目录"])
    项 = next((x for x in d["阶段"] if x["名称"] == a.阶段名), None)
    if not 项:
        print("未找到阶段：" + a.阶段名)
        return 1
    产物 = []
    for raw in a.产物:
        p = Path(raw)
        if not p.is_absolute():
            p = root / p
        p = p.resolve()
        if root not in p.parents and p != root:
            print("产物不在正式目录内：" + str(p))
            return 1
        if not p.exists() or not p.is_file() or p.stat().st_size == 0:
            print("产物不存在或为空：" + str(p))
            return 1
        产物.append({"路径": str(p), "字节": p.stat().st_size, "sha256": 摘要(p)})
    项.update({"状态": "completed", "产物": 产物, "完成时间": 时间(), "恢复说明": a.恢复说明 or ""})
    idx = d["阶段"].index(项)
    if idx + 1 < len(d["阶段"]):
        nxt = d["阶段"][idx + 1]
        if nxt["状态"] == "pending":
            nxt["状态"] = "in_progress"
        d["当前阶段"] = nxt["名称"]
    else:
        d["当前阶段"] = "全部完成"
    d["更新时间"] = 时间()
    原子写(a.清单, d)
    print(f"阶段已校验并完成：{a.阶段名}；登记产物{len(产物)}个。")
    return 0


def 验证(a):
    d = 读取(a.清单)
    失败 = []
    root = Path(d["正式目录"])
    if not root.exists():
        失败.append("正式目录不存在")
    for stage in d["阶段"]:
        if stage["状态"] == "completed":
            for x in stage.get("产物", []):
                p = Path(x["路径"])
                if not p.exists():
                    失败.append(f"{stage['名称']}产物缺失：{p}")
                elif p.stat().st_size != x["字节"] or 摘要(p) != x["sha256"]:
                    失败.append(f"{stage['名称']}产物已变化：{p}")
    running = [x["名称"] for x in d["阶段"] if x["状态"] == "in_progress"]
    if len(running) > 1:
        失败.append("同时存在多个in_progress阶段")
    if 失败:
        print("运行清单校验：未通过")
        for x in 失败:
            print("- " + x)
        return 1
    print(f"运行清单校验：通过；当前阶段：{d['当前阶段']}。")
    return 0


def 状态(a):
    d = 读取(a.清单)
    print(f"项目：{d['项目']}\n正式目录：{d['正式目录']}\n当前阶段：{d['当前阶段']}")
    for x in d["阶段"]:
        print(f"- {x['状态']}: {x['名称']}（产物{len(x.get('产物', []))}）")
    return 0


def 自检():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        art = root / "a.txt"
        art.write_text("ok", encoding="utf-8")
        manifest = root / "项目运行清单.json"
        a = argparse.Namespace(清单=manifest, 覆盖=False, 正式目录=str(root), 项目="自检项目", 最终成品="final.html", 阶段=["条件检查", "最终交付"])
        if 初始化(a):
            return 1
        b = argparse.Namespace(清单=manifest, 阶段名="条件检查", 产物=["a.txt"], 恢复说明="继续最终交付")
        if 完成(b) or 验证(argparse.Namespace(清单=manifest)):
            return 1
        art.write_text("changed", encoding="utf-8")
        if 验证(argparse.Namespace(清单=manifest)) == 0:
            print("项目检查点自检：篡改未被发现")
            return 1
    print("项目检查点自检：通过；原子清单、阶段推进、校验与变化检测有效。")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--自检", action="store_true")
    sub = p.add_subparsers(dest="命令")
    i = sub.add_parser("init")
    i.add_argument("清单", type=Path); i.add_argument("--项目", required=True); i.add_argument("--正式目录", required=True); i.add_argument("--最终成品", required=True); i.add_argument("--阶段", action="append"); i.add_argument("--覆盖", action="store_true")
    c = sub.add_parser("complete")
    c.add_argument("清单", type=Path); c.add_argument("--阶段名", required=True); c.add_argument("--产物", action="append", default=[]); c.add_argument("--恢复说明")
    for name in ("verify", "status"):
        x = sub.add_parser(name); x.add_argument("清单", type=Path)
    a = p.parse_args()
    if a.自检:
        return 自检()
    if a.命令 == "init": return 初始化(a)
    if a.命令 == "complete": return 完成(a)
    if a.命令 == "verify": return 验证(a)
    if a.命令 == "status": return 状态(a)
    p.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
