SELECT
    copies - IFNULL(br.borrowed_count, 0) AS copies_left
FROM items t
LEFT JOIN (
    SELECT item, COUNT(*) AS borrowed_count
    FROM borrows
    WHERE returned IS NULL
    GROUP BY item
) br ON t.id = br.item
WHERE id = ?