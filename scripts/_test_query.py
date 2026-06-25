import duckdb
con = duckdb.connect('greenlight.duckdb')
res = con.execute("""
SELECT 
    TRIM(director) as director,
    COUNT(*) as movie_count
FROM (
    SELECT UNNEST(string_split(directors, '|')) as director
    FROM movies 
    WHERE roi_is_real = true AND directors IS NOT NULL AND release_year >= 2020
)
WHERE TRIM(director) NOT IN (
    SELECT TRIM(UNNEST(string_split(directors, '|')))
    FROM movies 
    WHERE release_year < 2010 AND directors IS NOT NULL
)
GROUP BY 1 
HAVING COUNT(*) >= 2
LIMIT 5
""").fetchall()
print(res)
