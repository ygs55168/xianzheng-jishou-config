-- ============================================================
-- 2.3 本月开票数指标表
-- 表名: 开票数量指标表0630
-- ============================================================
IF OBJECT_ID('开票数量指标表0630', 'U') IS NOT NULL
    DROP TABLE 开票数量指标表0630;

CREATE TABLE 开票数量指标表0630 (
    单据年月 NVARCHAR(20),
    客户编码 NVARCHAR(100),
    客户名称 NVARCHAR(200),
    存货编码 NVARCHAR(100),
    存货名称 NVARCHAR(200),
    cdefine28 NVARCHAR(200),
    开票数量 DECIMAL(20,6)
);

INSERT INTO 开票数量指标表0630 (
    单据年月, 客户编码, 客户名称, 存货编码, 存货名称, cdefine28, 开票数量
)
SELECT
    CONVERT(VARCHAR(7), sl.dDate, 120) AS 单据年月,
    sl.cCusCode AS 客户编码,
    sl.cCusName AS 客户名称,
    sls.cInvCode AS 存货编码,
    sls.cInvName AS 存货名称,
    ISNULL(NULLIF(sls.cdefine28, ''), sls.cCusInvCode) AS cdefine28,
    SUM(sls.iquantity + sls.TBQuantity) AS 开票数量
FROM Salebillvouch sl  
INNER JOIN Salebillvouchs sls ON sl.sbvid = sls.sbvid  
INNER JOIN Customer c ON c.ccuscode = sl.cCusCode
    WHERE 1=1
    AND (
        -- 条件1：特殊开票备注客户
        (sl.cCusName = N'南京国电南自电网自动化有限公司' AND sl.cMemo IN (N'开发货单专用', N'销账 寄售'))
        OR
        -- 条件2：其余寄售客户，排除清单内客户
        (c.ccusdefine2 = 'T'
         AND sl.cCusName NOT IN (
            N'南京国电南自电网自动化有限公司'
        )
         AND sl.cCusName NOT IN (
            N'青岛海达源采购服务有限公司',
            N'青岛海尔零部件采购有限公司',
            N'佛山市顺德海尔智能电子有限公司',
            N'重庆海尔空调器有限公司'
        ))
    )
GROUP BY
    CONVERT(VARCHAR(7), sl.dDate, 120),
    sl.cCusCode, sl.cCusName, sls.cInvCode, sls.cInvName,
    ISNULL(NULLIF(sls.cdefine28, ''), sls.cCusInvCode);
