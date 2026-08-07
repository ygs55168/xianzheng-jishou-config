#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
先正寄售取数 - 配置校验脚本
读取 config.yaml，输出配置健康检查报告
用法: python validate_config.py [config文件路径]
"""
import sys
import os
import yaml
from datetime import datetime


# ─────────────────────────────────────────────
# 校验结果收集器
# ─────────────────────────────────────────────
class ValidationResult:
    def __init__(self):
        self.errors = []    # 错误：必须修复
        self.warnings = []  # 警告：建议修复
        self.infos = []     # 提示：可优化项

    def add_error(self, item, desc, targets="", fix=""):
        self.errors.append({"item": item, "desc": desc, "targets": targets, "fix": fix})

    def add_warning(self, item, desc, targets="", fix=""):
        self.warnings.append({"item": item, "desc": desc, "targets": targets, "fix": fix})

    def add_info(self, item, desc, targets="", fix=""):
        self.infos.append({"item": item, "desc": desc, "targets": targets, "fix": fix})

    @property
    def total(self):
        return len(self.errors) + len(self.warnings) + len(self.infos)

    @property
    def pass_rate(self):
        if self.total == 0:
            return 100.0
        passed = len(self.infos)  # 提示算通过
        return round(passed / self.total * 100, 1)


# ─────────────────────────────────────────────
# 各项校验逻辑
# ─────────────────────────────────────────────
def validate(cfg):
    r = ValidationResult()
    consign = cfg.get("consign_points", {})
    transfer = consign.get("transfer", [])
    dispatch = consign.get("dispatch", [])
    groups = cfg.get("group_mapping", [])
    invoice = cfg.get("invoice_rules", {})
    special_memo = invoice.get("special_memo_customers", [])
    exclude = invoice.get("summary_exclude_customers", [])
    qrcode = cfg.get("qrcode_customers", {})
    qr_list = qrcode.get("customers", [])
    meta = cfg.get("meta", {})

    # 所有寄售点客户名集合
    all_consign_names = set()
    for c in transfer + dispatch:
        name = c if isinstance(c, str) else c.get("name", "")
        if name:
            all_consign_names.add(name)

    # 所有寄售点（含编码）
    all_consign_list = []
    for c in transfer + dispatch:
        if isinstance(c, str):
            all_consign_list.append({"name": c, "code": "", "source": "transfer" if c in [x if isinstance(x, str) else x.get("name","") for x in transfer] else "dispatch"})
        else:
            src = "transfer" if c in transfer else "dispatch"
            all_consign_list.append({"name": c.get("name", ""), "code": c.get("code", ""), "source": src})

    # ── 1. 重复客户检查（同时出现在调拨单和发货退货单）
    transfer_names = set(c if isinstance(c, str) else c.get("name", "") for c in transfer)
    dispatch_names = set(c if isinstance(c, str) else c.get("name", "") for c in dispatch)
    dup = transfer_names & dispatch_names
    if dup:
        r.add_error(
            "重复客户检查",
            f"有 {len(dup)} 个客户同时出现在调拨单和发货退货单两个来源中，会导致数据重复统计",
            "、".join(sorted(dup)),
            "确认每个客户只属于一种来源类型，从其中一个列表中移除"
        )

    # ── 2. 重复客户编码检查
    code_map = {}
    for c in all_consign_list:
        code = c["code"].strip()
        if code:
            if code in code_map:
                code_map[code].append(c["name"])
            else:
                code_map[code] = [c["name"]]
    dup_codes = {k: v for k, v in code_map.items() if len(v) > 1}
    if dup_codes:
        for code, names in dup_codes.items():
            r.add_error(
                "重复客户编码检查",
                f"客户编码 [{code}] 被 {len(names)} 个客户共用",
                "、".join(names),
                "为每个客户分配唯一的客户编码"
            )

    # ── 3. 孤儿分组成员检查
    all_group_member_names = set()
    for g in groups:
        for m in g.get("members", []):
            name = m if isinstance(m, str) else m.get("name", "")
            if name:
                all_group_member_names.add(name)
    orphans = all_group_member_names - all_consign_names
    if orphans:
        r.add_warning(
            "孤儿分组成员检查",
            f"有 {len(orphans)} 个分组成员不在寄售点客户列表中",
            "、".join(sorted(orphans)),
            "检查客户名称拼写是否正确，或在寄售点中添加对应客户"
        )

    # ── 4. 未分组客户检查
    grouped_names = all_group_member_names
    ungrouped = all_consign_names - grouped_names
    if ungrouped:
        r.add_info(
            "未分组客户检查",
            f"有 {len(ungrouped)} 个寄售点客户未归属任何集团分组",
            "、".join(sorted(ungrouped)),
            "如需按集团汇总统计，请将这些客户加入对应分组"
        )

    # ── 5. 特殊开票客户缺失检查
    special_names = set()
    for s in special_memo:
        name = s if isinstance(s, str) else s.get("name", "")
        if name:
            special_names.add(name)
    missing_special = special_names - all_consign_names
    if missing_special:
        r.add_warning(
            "特殊开票客户缺失检查",
            f"有 {len(missing_special)} 个特殊开票备注客户不在寄售点列表中",
            "、".join(sorted(missing_special)),
            "确认客户名称是否正确，或在寄售点中添加对应客户"
        )

    # ── 6. 开票排除客户缺失检查
    exclude_set = set(exclude)
    missing_exclude = exclude_set - all_consign_names
    if missing_exclude:
        r.add_warning(
            "开票排除客户缺失检查",
            f"有 {len(missing_exclude)} 个开票排除客户不在寄售点列表中",
            "、".join(sorted(missing_exclude)),
            "确认客户名称是否正确，或移除无效的排除项"
        )

    # ── 7. 二维码客户缺失检查
    qr_set = set(qr_list)
    missing_qr = qr_set - all_consign_names
    if missing_qr:
        r.add_warning(
            "二维码客户缺失检查",
            f"有 {len(missing_qr)} 个二维码读入客户不在寄售点列表中",
            "、".join(sorted(missing_qr)),
            "确认客户名称是否正确，或在寄售点中添加对应客户"
        )

    # ── 8. 客户编码空值检查
    no_code = [c["name"] for c in all_consign_list if not c["code"].strip()]
    if no_code:
        r.add_info(
            "客户编码空值检查",
            f"有 {len(no_code)} 个寄售点客户未填写客户编码",
            "、".join(sorted(no_code)[:10]) + ("..." if len(no_code) > 10 else ""),
            "建议补充客户编码以便精确匹配"
        )

    # ── 9. 版本号格式检查
    version = meta.get("version", "")
    if version:
        if not version.replace("0", "").isdigit() and not version.isdigit():
            r.add_info(
                "版本号格式检查",
                f"版本号 [{version}] 不是纯数字格式",
                version,
                "建议使用 MMDD 格式（如 0630、0731），便于识别月份和日期"
            )
        elif len(version) < 2 or len(version) > 6:
            r.add_info(
                "版本号格式检查",
                f"版本号 [{version}] 长度异常",
                version,
                "建议使用 MMDD 格式（4位数字）"
            )

    # ── 10. 日期范围检查
    date_start = meta.get("date_start", "")
    date_end = meta.get("date_end", "")
    if date_start and date_end:
        try:
            ds = datetime.strptime(date_start, "%Y-%m-%d")
            de = datetime.strptime(date_end, "%Y-%m-%d")
            if ds > de:
                r.add_error(
                    "日期范围检查",
                    "开始日期晚于结束日期，会导致查询结果为空",
                    f"{date_start} → {date_end}",
                    "调整日期范围，确保开始日期早于结束日期"
                )
            elif ds == de:
                r.add_info(
                    "日期范围检查",
                    "开始日期与结束日期相同，仅查询一天的数据",
                    f"{date_start}",
                    "确认是否为单日查询，否则调整结束日期"
                )
        except ValueError as e:
            r.add_error(
                "日期范围检查",
                f"日期格式不正确: {e}",
                f"start={date_start}, end={date_end}",
                "请使用 YYYY-MM-DD 格式"
            )

    # ── 11. 分组成员重复检查
    for g in groups:
        gname = g.get("group_name", "")
        members = g.get("members", [])
        member_names = [m if isinstance(m, str) else m.get("name", "") for m in members]
        seen = set()
        dups = []
        for name in member_names:
            if name in seen:
                dups.append(name)
            seen.add(name)
        if dups:
            r.add_error(
                "分组成员重复检查",
                f"分组 [{gname}] 中有 {len(dups)} 个重复成员",
                "、".join(dups),
                f"从 [{gname}] 分组中移除重复的客户"
            )

    # ── 12. scope 一致性检查（业务规则校验）
    # 重庆海尔：收到场景只应包含物流公司，开票场景包含物流+空调器
    # 佳世达：收到场景只应包含电通公司，开票场景包含电通+电子
    scope_issues = []
    for g in groups:
        gname = g.get("group_name", "")
        members = g.get("members", [])
        if "重庆海尔" in gname:
            received_members = [m if isinstance(m, str) else m.get("name", "") for m in members
                                if isinstance(m, str) or m.get("scope", "both") in ("both", "received")]
            has_logistics = any("物流" in n for n in received_members)
            has_ac = any("空调器" in n for n in received_members)
            if has_ac and has_logistics:
                scope_issues.append(f"重庆海尔分组的收到场景同时包含物流公司和空调器公司，按业务规则收到只应以物流公司的调拨单为准")
        if "佳世达" in gname:
            received_members = [m if isinstance(m, str) else m.get("name", "") for m in members
                                if isinstance(m, str) or m.get("scope", "both") in ("both", "received")]
            has_diantong = any("电通" in n for n in received_members)
            has_dianzi = any("电子" in n for n in received_members)
            if has_dianzi and has_diantong:
                scope_issues.append(f"佳世达分组的收到场景同时包含电通公司和电子公司，按业务规则收到只应以电通公司的调拨单为准")
    if scope_issues:
        for issue in scope_issues:
            r.add_warning(
                "scope 一致性检查",
                issue,
                "",
                "调整对应分组成员的 scope 字段：收到场景的成员设为 received，仅开票场景的成员设为 invoiced，两者都算的设为 both"
            )

    return r


# ─────────────────────────────────────────────
# 报告输出
# ─────────────────────────────────────────────
def print_report(r, cfg_path):
    print("=" * 70)
    print("  先正寄售取数 - 配置健康检查报告")
    print("=" * 70)
    print(f"  配置文件: {cfg_path}")
    print(f"  检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 70)

    # 统计概览
    print()
    print("  📊 校验概览")
    print("  " + "-" * 50)
    print(f"  ❌ 错误: {len(r.errors)} 项")
    print(f"  ⚠️  警告: {len(r.warnings)} 项")
    print(f"  ℹ️  提示: {len(r.infos)} 项")
    print(f"  📋 总计: {r.total} 项")
    print(f"  ✅ 通过率: {r.pass_rate}%")
    print()

    def print_section(title, items, icon, color_code=""):
        if not items:
            return
        print(f"  {icon} {title} ({len(items)} 项)")
        print("  " + "─" * 50)
        for i, item in enumerate(items, 1):
            print(f"  [{i}] {item['item']}")
            print(f"      描述: {item['desc']}")
            if item['targets']:
                print(f"      涉及: {item['targets']}")
            if item['fix']:
                print(f"      建议: {item['fix']}")
            print()

    print_section("错误（必须修复）", r.errors, "❌")
    print_section("警告（建议修复）", r.warnings, "⚠️")
    print_section("提示（可优化）", r.infos, "ℹ️")

    print("=" * 70)
    if r.errors:
        print("  🔴 存在错误，请修复后再生成 SQL")
    elif r.warnings:
        print("  🟡 存在警告，建议检查确认")
    else:
        print("  🟢 配置校验通过，可以安全生成 SQL")
    print("=" * 70)


def export_report(r, cfg_path, output_path):
    """导出文本报告"""
    lines = []
    lines.append("=" * 70)
    lines.append("  先正寄售取数 - 配置健康检查报告")
    lines.append("=" * 70)
    lines.append(f"  配置文件: {cfg_path}")
    lines.append(f"  检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("-" * 70)
    lines.append("")
    lines.append("  校验概览")
    lines.append("  " + "-" * 50)
    lines.append(f"  错误: {len(r.errors)} 项")
    lines.append(f"  警告: {len(r.warnings)} 项")
    lines.append(f"  提示: {len(r.infos)} 项")
    lines.append(f"  总计: {r.total} 项")
    lines.append(f"  通过率: {r.pass_rate}%")
    lines.append("")

    def add_section(title, items):
        if not items:
            return
        lines.append(f"  {title} ({len(items)} 项)")
        lines.append("  " + "-" * 50)
        for i, item in enumerate(items, 1):
            lines.append(f"  [{i}] {item['item']}")
            lines.append(f"      描述: {item['desc']}")
            if item['targets']:
                lines.append(f"      涉及: {item['targets']}")
            if item['fix']:
                lines.append(f"      建议: {item['fix']}")
            lines.append("")

    add_section("错误（必须修复）", r.errors)
    add_section("警告（建议修复）", r.warnings)
    add_section("提示（可优化）", r.infos)

    lines.append("=" * 70)
    if r.errors:
        lines.append("  存在错误，请修复后再生成 SQL")
    elif r.warnings:
        lines.append("  存在警告，建议检查确认")
    else:
        lines.append("  配置校验通过，可以安全生成 SQL")
    lines.append("=" * 70)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_path


# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────
def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "先正寄售取数_config.yaml"

    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    result = validate(cfg)
    print_report(result, config_path)

    # 自动导出报告
    report_dir = "output_sql"
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "配置校验报告.txt")
    export_report(result, config_path, report_path)
    print(f"\n📄 报告已导出: {report_path}")

    # 有错误时返回非零退出码
    sys.exit(1 if result.errors else 0)


if __name__ == "__main__":
    main()
