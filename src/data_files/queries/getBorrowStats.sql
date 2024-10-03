SELECT
    user,
    COUNT(*) AS number_of_borrows,
    SUM(
        COALESCE(
            (julianday(COALESCE(returned, CURRENT_TIMESTAMP)) - julianday(retrieval_date)) * 24 * 60,
            0
        )
    ) AS total_borrow_time_minutes
FROM borrows
GROUP BY user;