WITH BorrowDurations AS (
    -- Calculate the duration each borrow has been active (whether returned or not) in seconds
    SELECT
        b.item,
        b.user,
        i.name AS item_name,
        CASE
            -- If the item has been returned, calculate the duration between retrieval and return in minutes
            WHEN b.returned IS NOT NULL THEN (JULIANDAY(b.returned) - JULIANDAY(b.retrieval_date)) * 24 * 60
            -- If the item has not been returned, calculate the duration until now in minutes
            ELSE (JULIANDAY('now') - JULIANDAY(b.retrieval_date)) * 24 * 60
        END AS borrow_duration
    FROM borrows b
    JOIN items i ON b.item = i.id
),
BorrowAggregates AS (
    -- Aggregate the durations by item and user
    SELECT
        item,
        user,
        SUM(borrow_duration) AS total_borrow_duration
    FROM BorrowDurations
    GROUP BY item, user
)
SELECT
    i.name,
    COUNT(b.user) AS total,
    SUM(bd.total_borrow_duration) AS time,
    u.user,
    MAX(bd.total_borrow_duration) AS usertime
FROM borrows b
JOIN items i ON b.item = i.id
JOIN BorrowAggregates bd ON b.item = bd.item
JOIN (
    -- Subquery to get the user who has borrowed each item for the longest time in seconds
    SELECT
        item,
        user,
        MAX(total_borrow_duration) AS longest_borrow_duration
    FROM BorrowAggregates
    GROUP BY item
) u ON bd.item = u.item AND bd.user = u.user
GROUP BY i.id
ORDER BY {} DESC;