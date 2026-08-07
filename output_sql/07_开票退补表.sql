-- ============================================================
-- 2.4 开票退补表（iTB 标记）
-- ============================================================
SELECT sl.cCusCode AS 客户编码, sl.cCusName AS 客户名称, sls.cInvCode AS 存货编码, sls.cInvName AS 存货名称,
    ISNULL(NULLIF(sls.cdefine28, ''), sls.cCusInvCode) AS cdefine28,
    sls.iTB AS 退补标记, sls.iQuantity AS 退补数量, sls.iquantity AS 开票数量
INTO 开票退补0630
FROM Salebillvouch sl
INNER JOIN Salebillvouchs sls ON sl.sbvid=sls.sbvid
INNER JOIN Customer c ON c.ccuscode=sl.cCusCode
WHERE 1=1
    AND c.ccusdefine2 = 'T'
    AND sl.dDate >= '2026-06-01 00:00:00.000'
    AND sl.dDate <= '2026-06-30 00:00:00.000'
    AND sls.iTB = '0';
