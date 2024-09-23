SELECT
    i.*,
    t.*,
    i.copies - IFNULL(br.borrowed_count, 0) AS available_copies
FROM {} t
JOIN items i USING (id)
LEFT JOIN (
    SELECT item, COUNT(*) AS borrowed_count
    FROM borrows
    JOIN items ON borrows.item = items.id
    WHERE items.type = ? AND borrows.returned IS NULL
    GROUP BY item
) br ON i.id = br.item
WHERE i.id = ?;