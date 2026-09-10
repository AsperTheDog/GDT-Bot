SELECT b.*, i.name AS item_name,
       CASE
           WHEN b.planned_return >= :now AND b.planned_return < datetime(:now, '+24 hours') THEN 'today'
           WHEN b.planned_return >= datetime(:now, '+24 hours') AND b.planned_return < datetime(:now, '+48 hours') THEN 'tomorrow'
           WHEN b.planned_return < :now THEN 'overdue'
       END AS return_status
FROM borrows b
JOIN items i ON i.id = b.item
WHERE b.planned_return IS NOT NULL
  AND b.planned_return <= datetime(:now, '+48 hours')
  AND b.returned IS NULL
  AND b.reminded = FALSE;
