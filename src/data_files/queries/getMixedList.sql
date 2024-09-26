SELECT
    b.user,
    i.name,
    i.id,
    i.type,
    i.copies - b.amount AS available_copies,
    b.amount,
    b.returned,
    b.retrieval_date
FROM
    items i
JOIN
    borrows b ON i.id = b.item {0}