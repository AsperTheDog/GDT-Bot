WITH table_info AS (
    SELECT
        i.*,
        t.*
    FROM
        items AS i
    JOIN
        {0} AS t USING (id)
    WHERE
        i.type = ?
)
SELECT * FROM table_info