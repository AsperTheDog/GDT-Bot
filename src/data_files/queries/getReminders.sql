SELECT *,
       CASE
           WHEN planned_return >= datetime('now') AND planned_return < datetime('now', '+24 hours') THEN 'today'
           WHEN planned_return >= datetime('now', '+24 hours') AND planned_return < datetime('now', '+48 hours') THEN 'tomorrow'
           WHEN planned_return < datetime('now') THEN 'overdue'
       END AS return_status
FROM borrows
WHERE planned_return IS NOT NULL
  AND planned_return <= datetime('now', '+48 hours')
  AND returned IS NULL
  AND reminded = FALSE;