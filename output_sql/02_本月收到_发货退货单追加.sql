-- ============================================================
-- 2.1.2 本月收到指标表 - 发货退货单（DispatchList）追加
-- 目标表: 寄售点数据指标表0630
-- ============================================================
INSERT INTO 寄售点数据指标表0630 (
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
    N'佛山市顺德区美的电热电器制造有限公司',
    N'合肥华凌股份有限公司',
    N'湖北美的电冰箱有限公司',
    N'广东美的希克斯电子有限公司',
    N'广州美的华凌冰箱有限公司',
    N'合肥美的希克斯电子有限公司',
    N'东芝家用电器制造（南海）有限公司',
    N'海信容声（扬州）冰箱有限公司',
    N'海信冰箱有限公司',
    N'海信容声（广东）冷柜有限公司',
    N'海信容声（广东）冰箱有限公司',
    N'海信（成都）冰箱有限公司',
    N'宁波德业变频技术有限公司',
    N'重庆海尔空调器有限公司',
    N'青岛海达源采购服务有限公司',
    N'苏州佳世达电子有限公司',
    N'四川长虹电器股份有限公司',
    N'比亚迪汽车工业有限公司',
    N'抚州比亚迪实业有限公司',
    N'广西东盟弗迪电池有限公司',
    N'广西弗迪电池有限公司',
    N'宁波弗迪电池有限公司',
    N'汕尾比亚迪汽车有限公司',
    N'绍兴弗迪电池有限公司',
    N'深圳比亚迪汽车实业有限公司',
    N'深圳市比亚迪供应链管理有限公司',
    N'西安比亚迪汽车零部件有限公司',
    N'长沙市比亚迪汽车有限公司',
    N'郑州比亚迪汽车有限公司',
    N'重庆弗迪锂电池有限公司',
    N'东莞弗迪动力有限公司',
    N'广东美的智能科技有限公司',
    N'广东美创希科技有限公司'
)
GROUP BY
    CAST(YEAR(dl.dDate) AS NVARCHAR)+'-'+CAST(MONTH(dl.dDate) AS NVARCHAR),
    dl.cCusCode, dl.cCusName, dls.cdefine28, dls.cInvCode, dls.cInvName
ORDER BY
    CAST(YEAR(dl.dDate) AS NVARCHAR)+'-'+CAST(MONTH(dl.dDate) AS NVARCHAR) DESC;
