WITH table_info AS (
    SELECT
        i.name,
        i.type,
        i.copies,
        t.*
    FROM
        items AS i
    JOIN
        {0} AS t ON i.id = t.id
    WHERE
        i.type = ?
)
SELECT * FROM table_info