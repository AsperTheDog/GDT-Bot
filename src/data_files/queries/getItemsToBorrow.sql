SELECT i.id
FROM items i
LEFT JOIN (
    SELECT item, SUM(amount) AS borrowed_amount
    FROM borrows
    WHERE returned IS NULL
    GROUP BY item
) b ON i.id = b.item
WHERE i.name LIKE '%' || ? || '%'
AND (i.copies > IFNULL(b.borrowed_amount, 0))
AND i.id NOT IN (
    SELECT item
    FROM borrows
    WHERE user = ?
    AND returned IS NULL
);