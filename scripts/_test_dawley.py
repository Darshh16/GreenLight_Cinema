import duckdb
con = duckdb.connect('greenlight.duckdb')
res = con.execute("SELECT title, release_year FROM movies WHERE directors LIKE '%Searle Dawley%'").fetchall()
print(res)
