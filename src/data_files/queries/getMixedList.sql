SELECT * FROM (
    SELECT b.user, bg.name AS item_name, 'boardgame' AS item_type,
           (bg.copies - IFNULL(borrowed_counts.total_borrowed, 0)) AS available_copies
    FROM borrows b
    JOIN boardgames bg ON b.item = bg.id
    LEFT JOIN (
        SELECT item, type, SUM(amount) AS total_borrowed
        FROM borrows
        WHERE type = 'boardgame'
        GROUP BY item, type
    ) AS borrowed_counts ON b.item = borrowed_counts.item AND b.type = borrowed_counts.type
    WHERE b.type = 'boardgame' {0}

    UNION ALL

    SELECT b.user, vg.name AS item_name, 'videogame' AS item_type,
           (vg.copies - IFNULL(borrowed_counts.total_borrowed, 0)) AS available_copies
    FROM borrows b
    JOIN videogames vg ON b.item = vg.id
    LEFT JOIN (
        SELECT item, type, SUM(amount) AS total_borrowed
        FROM borrows
        WHERE type = 'videogame'
        GROUP BY item, type
    ) AS borrowed_counts ON b.item = borrowed_counts.item AND b.type = borrowed_counts.type
    WHERE b.type = 'videogame' {0}

    UNION ALL

    SELECT b.user, bk.name AS item_name, 'book' AS item_type,
           (bk.copies - IFNULL(borrowed_counts.total_borrowed, 0)) AS available_copies
    FROM borrows b
    JOIN books bk ON b.item = bk.id
    LEFT JOIN (
        SELECT item, type, SUM(amount) AS total_borrowed
        FROM borrows
        WHERE type = 'book'
        GROUP BY item, type
    ) AS borrowed_counts ON b.item = borrowed_counts.item AND b.type = borrowed_counts.type
    WHERE b.type = 'book' {0}
) AS combined_results {1};