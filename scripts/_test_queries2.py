import duckdb
con = duckdb.connect('greenlight.duckdb')

print("TOP DIRECTORS:")
res = con.execute("""
SELECT TRIM(director) as director, COUNT(*) FROM (
    SELECT UNNEST(string_split(directors, '|')) as director
    FROM movies 
    WHERE roi_is_real = true AND directors IS NOT NULL AND release_year >= 2010
)
WHERE TRIM(director) NOT IN (
    SELECT TRIM(UNNEST(string_split(directors, '|')))
    FROM movies WHERE release_year < 2000 AND directors IS NOT NULL
)
GROUP BY 1 HAVING COUNT(*) >= 2 ORDER BY COUNT(*) DESC LIMIT 5
""").fetchall()
print(res)

print("TOP ACTORS:")
res = con.execute("""
SELECT TRIM(actor) as actor, COUNT(*) FROM (
    SELECT UNNEST(string_split(top_cast, '|')) as actor
    FROM movies 
    WHERE roi_is_real = true AND top_cast IS NOT NULL AND release_year >= 2010
)
GROUP BY 1 HAVING COUNT(*) >= 2 ORDER BY COUNT(*) DESC LIMIT 5
""").fetchall()
print(res)

print("EMERGING:")
res = con.execute("""
SELECT TRIM(name) as name, COUNT(*) FROM (
    SELECT UNNEST(string_split(directors, '|')) as name FROM movies WHERE roi_is_real = true AND release_year >= 2015
    UNION ALL
    SELECT UNNEST(string_split(top_cast, '|')) as name FROM movies WHERE roi_is_real = true AND release_year >= 2015
)
WHERE TRIM(name) NOT IN (
    SELECT TRIM(UNNEST(string_split(directors, '|'))) FROM movies WHERE release_year < 2015 AND directors IS NOT NULL
    UNION ALL
    SELECT TRIM(UNNEST(string_split(top_cast, '|'))) FROM movies WHERE release_year < 2015 AND top_cast IS NOT NULL
)
GROUP BY 1 HAVING COUNT(*) >= 2 AND COUNT(*) <= 4 ORDER BY COUNT(*) DESC LIMIT 5
""").fetchall()
print(res)
