SELECT i.id
FROM items i
JOIN borrows b ON i.id = b.item
WHERE {}
AND b.user = ?
AND b.returned IS NULL;