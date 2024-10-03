SELECT
    user,
    COUNT(*) AS total,
    SUM(COALESCE((julianday(COALESCE(returned, CURRENT_TIMESTAMP)) - julianday(retrieval_date)) * 24 * 60, 0)) AS time,
    COUNT(CASE WHEN returned IS NULL THEN 1 END) AS current
FROM borrows
GROUP BY user ORDER BY {} DESC