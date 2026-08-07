#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
先正寄售取数 - SQL 渲染脚本
读取 config.yaml，自动生成全套建表/取数 SQL
用法: python render_sql.py [config文件路径]
"""
import sys
import os
import yaml


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────
def sql_str(s):
    """生成 SQL Server 字符串字面量"""
    return "N'" + s.replace("'", "''") + "'"


def sql_in_list(custs, indent="    "):
    """生成 IN 子句，每行一个客户名"""
    lines = []
    for i, c in enumerate(custs):
        comma = "," if i < len(custs) - 1 else ""
        lines.append(f"{indent}{sql_str(c)}{comma}")
    return "\n".join(lines)


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_cust_names(lst):
    """从客户列表中提取名称"""
    return [c if isinstance(c, str) else c.get("name", "") for c in lst]


def build_case_when(groups, scope_filter=None):
    """
    生成分组 CASE WHEN 语句
    scope_filter: None=不过滤, 'received'=只看收到场景, 'invoiced'=只看开票场景
    """
    lines = ["CASE"]
    for g in groups:
        gname = g["group_name"]
        members = g.get("members", [])
        for m in members:
            mname = m if isinstance(m, str) else m.get("name", "")
            mscope = "both" if isinstance(m, str) else m.get("scope", "both")
            # 按 scope 过滤
            if scope_filter == "received" and mscope not in ("both", "received"):
                continue
            if scope_filter == "invoiced" and mscope not in ("both", "invoiced"):
                continue
            lines.append(f"    WHEN 客户名称 = {sql_str(mname)} THEN {sql_str(gname)}")
    # 简写分组名直接匹配
    group_names = [g["group_name"] for g in groups]
    if group_names:
        in_clause = ", ".join(sql_str(g) for g in group_names)
        lines.append(f"    WHEN 客户名称 IN ({in_clause}) THEN 客户名称")
    lines.append("    ELSE 客户名称")
    lines.append("END")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 各段 SQL 生成
# ─────────────────────────────────────────────
def sql_received_transfer(cfg):
    """2.1.1 本月收到 - 调拨单"""
    consign = cfg["consign_points"]
    transfer = get_cust_names(consign["transfer"])
    m = cfg["meta"]
    ver = m["version"]
    cust_expr = m["cust_item_no_expr"]

    custs = sql_in_list(transfer)
    return f"""-- ============================================================
-- 2.1.1 本月收到指标表 - 调拨单（TransVouch）
-- 表名: 寄售点数据指标表{ver}
-- ============================================================
SELECT 
    a.*,
    slss.iSettleQuantity AS 开票数量
INTO 寄售点数据指标表{ver}
FROM 
(
    SELECT   
        CAST(YEAR(tv.dTVDate) AS NVARCHAR)+'-'+CAST(MONTH(tv.dTVDate) AS NVARCHAR) AS 单据年月,
        c.cCusCode AS 客户编码,
        c.cCusName AS 客户名称,
        tvs.cInvCode AS 存货编码,
        i.cInvName AS 存货名称,
        tvs.cDefine31 AS 客户料号,
        SUM(tvs.iTVQuantity) AS 调拨数量
    FROM TransVouch tv
    INNER JOIN TransVouchs tvs ON tv.ctvcode = tvs.ctvcode
    LEFT JOIN Customer c ON tv.cdefine14 = c.ccusname
    LEFT JOIN Inventory i ON tvs.cInvCode = i.cInvCode 
    WHERE c.ccusname IN (
{custs}
    )
    GROUP BY 
        CAST(YEAR(tv.dTVDate) AS NVARCHAR)+'-'+CAST(MONTH(tv.dTVDate) AS NVARCHAR),
        c.cCusCode, c.cCusName, tvs.cDefine31, tvs.cInvCode, i.cInvName
) a 
LEFT JOIN 
(
    SELECT
        CAST(YEAR(sl.dDate) AS NVARCHAR)+'-'+CAST(MONTH(sl.dDate) AS NVARCHAR) AS 单据年月,
        sl.cCusCode, sl.cCusName, sls.cInvCode, sls.cInvName,
        {cust_expr} AS cdefine28,
        SUM(sls.iquantity) AS iSettleQuantity
    FROM Salebillvouch sl  
    INNER JOIN Salebillvouchs sls ON sl.sbvid = sls.sbvid  
    WHERE sl.cCusName IN (
{custs}
    )
    GROUP BY 
        CAST(YEAR(sl.dDate) AS NVARCHAR)+'-'+CAST(MONTH(sl.dDate) AS NVARCHAR),
        sl.cCusCode, sl.cCusName, sls.cInvCode, sls.cInvName,
        {cust_expr}
) slss 
ON a.单据年月 = slss.单据年月 
AND a.客户名称 = slss.cCusName
AND a.存货编码 = slss.cInvCode 
AND a.客户料号 = slss.cdefine28;
"""


def sql_received_dispatch(cfg):
    """2.1.2 本月收到 - 发货退货单追加"""
    consign = cfg["consign_points"]
    dispatch = get_cust_names(consign["dispatch"])
    m = cfg["meta"]
    ver = m["version"]

    custs = sql_in_list(dispatch)
    return f"""-- ============================================================
-- 2.1.2 本月收到指标表 - 发货退货单（DispatchList）追加
-- 目标表: 寄售点数据指标表{ver}
-- ============================================================
INSERT INTO 寄售点数据指标表{ver} (
    单据年月, 客户编码, 客户名称, 存货编码, 存货名称,
    客户料号, 调拨数量, 开票数量
)
SELECT
    CAST(YEAR(dl.dDate) AS NVARCHAR)+'-'+CAST(MONTH(dl.dDate) AS NVARCHAR) AS 单据年月,
    dl.cCusCode AS 客户编码,
    dl.cCusName AS 客户名称,
    dls.cInvCode AS 存货编码,
    dls.cInvName AS 存货名称,
    dls.cdefine28 AS 客户料号,
    SUM(dls.iQuantity) AS 调拨数量,
    SUM(dls.iSettleQuantity) AS 开票数量
FROM DispatchList dl
INNER JOIN DispatchLists dls ON dl.DLID = dls.DLID
WHERE dl.cCusName IN (
{custs}
)
GROUP BY
    CAST(YEAR(dl.dDate) AS NVARCHAR)+'-'+CAST(MONTH(dl.dDate) AS NVARCHAR),
    dl.cCusCode, dl.cCusName, dls.cdefine28, dls.cInvCode, dls.cInvName
ORDER BY
    CAST(YEAR(dl.dDate) AS NVARCHAR)+'-'+CAST(MONTH(dl.dDate) AS NVARCHAR) DESC;
"""


def sql_invoiced_metrics(cfg):
    """2.3 本月开票数指标表"""
    m = cfg["meta"]
    ver = m["version"]
    cust_expr = m["cust_item_no_expr"]
    invoice = cfg["invoice_rules"]
    special = invoice.get("special_memo_customers", [])
    exclude = invoice.get("summary_exclude_customers", [])
    flag_field = m["consign_flag_field"]
    flag_val = m["consign_flag_value"]

    # 特殊备注条件
    memo_conditions = []
    for s in special:
        sname = s if isinstance(s, str) else s.get("name", "")
        memos = s if isinstance(s, str) else s.get("memos", [])
        if memos:
            memo_list = ", ".join(sql_str(memo) for memo in memos)
            memo_conditions.append(
                f"(sl.cCusName = {sql_str(sname)} AND sl.cMemo IN ({memo_list}))"
            )

    memo_clause = "\n        OR ".join(memo_conditions) if memo_conditions else ""

    # 排除清单
    exclude_clause = ""
    if exclude:
        exclude_list = sql_in_list(exclude, indent="            ")
        exclude_clause = f"AND sl.cCusName NOT IN (\n{exclude_list}\n        )"

    where_clause = f"""    WHERE 1=1
    AND (
        -- 条件1：特殊开票备注客户
        {memo_clause}
        OR
        -- 条件2：其余寄售客户，排除清单内客户
        (c.{flag_field} = '{flag_val}'
         AND sl.cCusName NOT IN (
            {', '.join(sql_str(s.get('name','') if isinstance(s, dict) else s) for s in special)}
        )
         {exclude_clause})
    )"""

    return f"""-- ============================================================
-- 2.3 本月开票数指标表
-- 表名: 开票数量指标表{ver}
-- ============================================================
IF OBJECT_ID('开票数量指标表{ver}', 'U') IS NOT NULL
    DROP TABLE 开票数量指标表{ver};

CREATE TABLE 开票数量指标表{ver} (
    单据年月 NVARCHAR(20),
    客户编码 NVARCHAR(100),
    客户名称 NVARCHAR(200),
    存货编码 NVARCHAR(100),
    存货名称 NVARCHAR(200),
    cdefine28 NVARCHAR(200),
    开票数量 DECIMAL(20,6)
);

INSERT INTO 开票数量指标表{ver} (
    单据年月, 客户编码, 客户名称, 存货编码, 存货名称, cdefine28, 开票数量
)
SELECT
    CONVERT(VARCHAR(7), sl.dDate, 120) AS 单据年月,
    sl.cCusCode AS 客户编码,
    sl.cCusName AS 客户名称,
    sls.cInvCode AS 存货编码,
    sls.cInvName AS 存货名称,
    {cust_expr} AS cdefine28,
    SUM(sls.iquantity + sls.TBQuantity) AS 开票数量
FROM Salebillvouch sl  
INNER JOIN Salebillvouchs sls ON sl.sbvid = sls.sbvid  
INNER JOIN Customer c ON c.ccuscode = sl.cCusCode
{where_clause}
GROUP BY
    CONVERT(VARCHAR(7), sl.dDate, 120),
    sl.cCusCode, sl.cCusName, sls.cInvCode, sls.cInvName,
    {cust_expr};
"""


def sql_group_update_received(cfg):
    """2.5.1 收到表 - 分组客户名称回填"""
    m = cfg["meta"]
    ver = m["version"]
    groups = cfg["group_mapping"]
    case_when = build_case_when(groups, scope_filter="received")

    return f"""-- ============================================================
-- 2.5.1 本月收到 - 添加分组客户名称字段
-- 目标表: 寄售点数据指标表{ver}
-- ============================================================
ALTER TABLE 寄售点数据指标表{ver}
ADD 分组客户名称 NVARCHAR(200) NULL;
GO

UPDATE 寄售点数据指标表{ver}
SET 分组客户名称 = 
{case_when};
GO
"""


def sql_group_update_invoiced(cfg):
    """2.5.2 开票表 - 分组客户名称回填"""
    m = cfg["meta"]
    ver = m["version"]
    groups = cfg["group_mapping"]
    case_when = build_case_when(groups, scope_filter="invoiced")

    return f"""-- ============================================================
-- 2.5.2 本月开票 - 添加分组客户名称字段
-- 目标表: 开票数量指标表{ver}
-- ============================================================
ALTER TABLE 开票数量指标表{ver}
ADD 分组客户名称 NVARCHAR(200) NULL;
GO

UPDATE 开票数量指标表{ver}
SET 分组客户名称 = 
{case_when};
GO
"""


def sql_unbilled_summary(cfg):
    """2.2 本月未开票数存货编码名称映射汇总表"""
    ver = cfg["meta"]["version"]
    return f"""-- ============================================================
-- 2.2 本月未开票数存货编码名称映射汇总表
-- ============================================================
SELECT t.客户名称, t.存货编码, t.单据年月,
    存货名称 = STUFF((SELECT DISTINCT '、'+ISNULL(i2.存货名称,'') FROM 寄售未开票{ver} i2
        WHERE i2.客户名称=t.客户名称 AND i2.存货编码=t.存货编码 FOR XML PATH('')),1,1,''),
    SUM(ISNULL(t.未开票数量,0)) AS 未开票数量存货编码合计
INTO 本月未开票数存货编码名称映射汇总表{ver}
FROM 寄售未开票{ver} t
WHERE 1=1
GROUP BY t.客户名称, t.存货编码, t.单据年月;
"""


def sql_invoice_tb(cfg):
    """2.4 开票退补表"""
    m = cfg["meta"]
    ver = m["version"]
    cust_expr = m["cust_item_no_expr"]
    flag_field = m["consign_flag_field"]
    flag_val = m["consign_flag_value"]

    return f"""-- ============================================================
-- 2.4 开票退补表（iTB 标记）
-- ============================================================
SELECT sl.cCusCode AS 客户编码, sl.cCusName AS 客户名称, sls.cInvCode AS 存货编码, sls.cInvName AS 存货名称,
    {cust_expr} AS cdefine28,
    sls.iTB AS 退补标记, sls.iQuantity AS 退补数量, sls.iquantity AS 开票数量
INTO 开票退补{ver}
FROM Salebillvouch sl
INNER JOIN Salebillvouchs sls ON sl.sbvid=sls.sbvid
INNER JOIN Customer c ON c.ccuscode=sl.cCusCode
WHERE 1=1
    AND c.{flag_field} = '{flag_val}'
    AND sl.dDate >= '{m['date_start']} 00:00:00.000'
    AND sl.dDate <= '{m['date_end']} 00:00:00.000'
    AND sls.iTB = '0';
"""


def sql_received_inv_summary(cfg):
    """2.6.1.1 本月收到数存货编码名称映射汇总表"""
    m = cfg["meta"]
    ver = m["version"]
    ps = m["period_short"]

    return f"""-- ============================================================
-- 2.6.1.1 本月收到数存货编码名称映射汇总表
-- ============================================================
SELECT t.客户名称, t.存货编码, t.单据年月,
    存货名称 = STUFF((SELECT DISTINCT '、'+ISNULL(i2.存货名称,'') FROM 寄售点数据指标表{ver} i2
        WHERE i2.客户名称=t.客户名称 AND i2.存货编码=t.存货编码 FOR XML PATH('')),1,1,''),
    SUM(ISNULL(t.调拨数量,0)) AS 调拨单存货编码合计
INTO 本月收到数存货编码名称映射汇总表{ver}
FROM 寄售点数据指标表{ver} t
WHERE 单据年月 = '{ps}'
GROUP BY t.客户名称, t.存货编码, t.单据年月;
"""


def sql_received_group_inv_summary(cfg):
    """2.6.1.2 本月收到数分组存货编码名称映射汇总表"""
    m = cfg["meta"]
    ver = m["version"]
    ps = m["period_short"]

    return f"""-- ============================================================
-- 2.6.1.2 本月收到数分组存货编码名称映射汇总表
-- ============================================================
SELECT t.分组客户名称, t.存货编码, t.单据年月,
    存货名称 = STUFF((SELECT DISTINCT '、'+ISNULL(i2.存货名称,'') FROM 寄售点数据指标表{ver} i2
        WHERE i2.分组客户名称=t.分组客户名称 AND i2.存货编码=t.存货编码 AND i2.单据年月=t.单据年月 FOR XML PATH('')),1,1,''),
    SUM(ISNULL(t.调拨数量,0)) AS 调拨单存货编码合计
INTO 本月收到数分组存货编码名称映射汇总表{ver}
FROM 寄售点数据指标表{ver} t
WHERE 单据年月 = '{ps}'
GROUP BY t.分组客户名称, t.存货编码, t.单据年月;
"""


def sql_invoiced_inv_summary(cfg):
    """2.6.2 本月开票（分组+客户）存货编码名称映射汇总表"""
    m = cfg["meta"]
    ver = m["version"]
    pf = m["period_full"]

    return f"""-- ============================================================
-- 2.6.2 本月开票（分组+客户）存货编码名称映射汇总表
-- ============================================================
IF OBJECT_ID(N'dbo.本月开票分组数存货编码名称映射汇总表{ver}', N'U') IS NOT NULL
    DROP TABLE dbo.本月开票分组数存货编码名称映射汇总表{ver};
GO

SELECT t.分组客户名称, t.存货编码, t.单据年月,
    存货名称 = STUFF((SELECT DISTINCT '、'+ISNULL(i2.存货名称,'') FROM 开票数量指标表{ver} i2
        WHERE i2.分组客户名称=t.分组客户名称 AND i2.存货编码=t.存货编码 AND i2.单据年月=t.单据年月 FOR XML PATH('')),1,1,''),
    SUM(ISNULL(t.开票数量,0)) AS 开票数量存货编码合计
INTO 本月开票分组数存货编码名称映射汇总表{ver}
FROM 开票数量指标表{ver} t
WHERE t.单据年月 = '{pf}'
GROUP BY t.分组客户名称, t.存货编码, t.单据年月;
GO

IF OBJECT_ID(N'dbo.本月开票数存货编码名称映射汇总表{ver}', N'U') IS NOT NULL
    DROP TABLE dbo.本月开票数存货编码名称映射汇总表{ver};
GO

SELECT t.客户名称, t.存货编码, t.单据年月,
    存货名称 = STUFF((SELECT DISTINCT '、'+ISNULL(i2.存货名称,'') FROM 开票数量指标表{ver} i2
        WHERE i2.客户名称=t.客户名称 AND i2.存货编码=t.存货编码 AND i2.单据年月=t.单据年月 FOR XML PATH('')),1,1,''),
    SUM(ISNULL(t.开票数量,0)) AS 开票数量存货编码合计
INTO 本月开票数存货编码名称映射汇总表{ver}
FROM 开票数量指标表{ver} t
WHERE t.单据年月 = '{pf}'
GROUP BY t.客户名称, t.存货编码, t.单据年月;
GO
"""


def sql_qrcode_note(cfg):
    """二维码读入客户说明"""
    qr = cfg.get("qrcode_customers", {})
    if not qr.get("enabled", False):
        return ""
    customers = qr.get("customers", [])
    custs = sql_in_list(customers)
    scan_field = qr.get("scan_field", "cdefine31")
    fallback = qr.get("fallback_field", "cCusInvCode")

    return f"""-- ============================================================
-- 二维码读入客户说明
-- 这些客户的客户料号通过扫码读入到 {scan_field} 字段
-- 空值回退到 {fallback}
-- ============================================================
-- 客户清单：
{custs}
-- ============================================================
"""


# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────
def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "先正寄售取数_config.yaml"

    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)

    cfg = load_config(config_path)
    ver = cfg["meta"]["version"]
    output_dir = "output_sql"
    os.makedirs(output_dir, exist_ok=True)

    # 定义输出文件列表（按业务流程顺序）
    files = [
        ("01_本月收到_调拨单.sql", sql_received_transfer(cfg)),
        ("02_本月收到_发货退货单追加.sql", sql_received_dispatch(cfg)),
        ("03_本月开票数指标表.sql", sql_invoiced_metrics(cfg)),
        ("04_收到表_分组回填.sql", sql_group_update_received(cfg)),
        ("05_开票表_分组回填.sql", sql_group_update_invoiced(cfg)),
        ("06_本月未开票汇总表.sql", sql_unbilled_summary(cfg)),
        ("07_开票退补表.sql", sql_invoice_tb(cfg)),
        ("08_收到_存货编码汇总.sql", sql_received_inv_summary(cfg)),
        ("09_收到_分组存货编码汇总.sql", sql_received_group_inv_summary(cfg)),
        ("10_开票_存货编码汇总.sql", sql_invoiced_inv_summary(cfg)),
        ("11_二维码读入说明.sql", sql_qrcode_note(cfg)),
    ]

    print("=" * 60)
    print(f"  先正寄售取数 SQL 生成器")
    print(f"  版本: {ver}")
    print("=" * 60)

    total_size = 0
    for fname, content in files:
        if not content.strip():
            continue
        fpath = os.path.join(output_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        size = len(content)
        total_size += size
        print(f"  ✅ {fname}  ({size:,} 字符)")

    print("-" * 60)
    print(f"  共生成 {len([f for f, c in files if c.strip()])} 个 SQL 文件")
    print(f"  输出目录: {output_dir}/")
    print(f"  调拨单客户: {len(cfg['consign_points']['transfer'])} 家")
    print(f"  发货退货单客户: {len(cfg['consign_points']['dispatch'])} 家")
    print(f"  集团分组: {len(cfg['group_mapping'])} 个")
    print("=" * 60)


if __name__ == "__main__":
    main()
