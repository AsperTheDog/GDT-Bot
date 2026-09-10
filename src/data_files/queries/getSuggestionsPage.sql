SELECT s.*, COUNT(v.user) AS votes
FROM suggestions s
LEFT JOIN suggestion_votes v ON v.name = s.name{0}
GROUP BY s.name
ORDER BY votes DESC, s.name ASC
