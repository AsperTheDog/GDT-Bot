WITH table_info AS (SELECT
    i.*,
    t.*,
    GROUP_CONCAT(c.category, ',') AS categories,
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
LEFT JOIN categories c using (id)
GROUP BY id
) SELECT * FROM table_info