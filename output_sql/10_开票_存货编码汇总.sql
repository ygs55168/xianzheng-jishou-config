-- ============================================================
-- 2.6.2 本月开票（分组+客户）存货编码名称映射汇总表
-- ============================================================
IF OBJECT_ID(N'dbo.本月开票分组数存货编码名称映射汇总表0630', N'U') IS NOT NULL
    DROP TABLE dbo.本月开票分组数存货编码名称映射汇总表0630;
GO

SELECT t.分组客户名称, t.存货编码, t.单据年月,
    存货名称 = STUFF((SELECT DISTINCT '、'+ISNULL(i2.存货名称,'') FROM 开票数量指标表0630 i2
        WHERE i2.分组客户名称=t.分组客户名称 AND i2.存货编码=t.存货编码 AND i2.单据年月=t.单据年月 FOR XML PATH('')),1,1,''),
    SUM(ISNULL(t.开票数量,0)) AS 开票数量存货编码合计
INTO 本月开票分组数存货编码名称映射汇总表0630
FROM 开票数量指标表0630 t
WHERE t.单据年月 = '2026-06'
GROUP BY t.分组客户名称, t.存货编码, t.单据年月;
GO

IF OBJECT_ID(N'dbo.本月开票数存货编码名称映射汇总表0630', N'U') IS NOT NULL
    DROP TABLE dbo.本月开票数存货编码名称映射汇总表0630;
GO

SELECT t.客户名称, t.存货编码, t.单据年月,
    存货名称 = STUFF((SELECT DISTINCT '、'+ISNULL(i2.存货名称,'') FROM 开票数量指标表0630 i2
        WHERE i2.客户名称=t.客户名称 AND i2.存货编码=t.存货编码 AND i2.单据年月=t.单据年月 FOR XML PATH('')),1,1,''),
    SUM(ISNULL(t.开票数量,0)) AS 开票数量存货编码合计
INTO 本月开票数存货编码名称映射汇总表0630
FROM 开票数量指标表0630 t
WHERE t.单据年月 = '2026-06'
GROUP BY t.客户名称, t.存货编码, t.单据年月;
GO
