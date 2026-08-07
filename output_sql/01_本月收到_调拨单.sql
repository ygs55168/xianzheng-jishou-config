-- ============================================================
-- 2.1.1 本月收到指标表 - 调拨单（TransVouch）
-- 表名: 寄售点数据指标表0630
-- ============================================================
SELECT 
    a.*,
    slss.iSettleQuantity AS 开票数量
INTO 寄售点数据指标表0630
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
    N'无锡飞翎电子有限公司',
    N'江苏美的清洁电器股份有限公司',
    N'合肥美的洗衣机有限公司',
    N'小天鹅（荆州）三金电器有限公司',
    N'湖北美的洗衣机有限公司',
    N'合肥市航嘉电子技术有限公司',
    N'南京国电南自电网自动化有限公司',
    N'佛山市顺德海尔智能电子有限公司',
    N'青岛海尔零部件采购有限公司',
    N'重庆海尔物流有限公司',
    N'广东美的集团芜湖制冷设备有限公司',
    N'美的集团武汉制冷设备有限公司',
    N'美的集团武汉暖通设备有限公司',
    N'邯郸美的制冷设备有限公司',
    N'重庆美的制冷设备有限公司',
    N'广东美的制冷设备有限公司',
    N'广州华凌制冷设备有限公司',
    N'苏州佳世达电通有限公司',
    N'杭州松下家用电器有限公司'
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
        ISNULL(NULLIF(sls.cdefine28, ''), sls.cCusInvCode) AS cdefine28,
        SUM(sls.iquantity) AS iSettleQuantity
    FROM Salebillvouch sl  
    INNER JOIN Salebillvouchs sls ON sl.sbvid = sls.sbvid  
    WHERE sl.cCusName IN (
    N'无锡飞翎电子有限公司',
    N'江苏美的清洁电器股份有限公司',
    N'合肥美的洗衣机有限公司',
    N'小天鹅（荆州）三金电器有限公司',
    N'湖北美的洗衣机有限公司',
    N'合肥市航嘉电子技术有限公司',
    N'南京国电南自电网自动化有限公司',
    N'佛山市顺德海尔智能电子有限公司',
    N'青岛海尔零部件采购有限公司',
    N'重庆海尔物流有限公司',
    N'广东美的集团芜湖制冷设备有限公司',
    N'美的集团武汉制冷设备有限公司',
    N'美的集团武汉暖通设备有限公司',
    N'邯郸美的制冷设备有限公司',
    N'重庆美的制冷设备有限公司',
    N'广东美的制冷设备有限公司',
    N'广州华凌制冷设备有限公司',
    N'苏州佳世达电通有限公司',
    N'杭州松下家用电器有限公司'
    )
    GROUP BY 
        CAST(YEAR(sl.dDate) AS NVARCHAR)+'-'+CAST(MONTH(sl.dDate) AS NVARCHAR),
        sl.cCusCode, sl.cCusName, sls.cInvCode, sls.cInvName,
        ISNULL(NULLIF(sls.cdefine28, ''), sls.cCusInvCode)
) slss 
ON a.单据年月 = slss.单据年月 
AND a.客户名称 = slss.cCusName
AND a.存货编码 = slss.cInvCode 
AND a.客户料号 = slss.cdefine28;
