SELECT i.id
FROM items i
JOIN borrows b ON i.id = b.item
WHERE b.user = ?
AND i.name LIKE '%' || ? || '%'
AND b.returned IS NULL;