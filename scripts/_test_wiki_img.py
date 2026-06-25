import requests
import urllib.parse

def get_image(name):
    url = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(name)}&prop=pageimages&format=json&pithumbsize=200"
    headers = {"User-Agent": "GreenlightCinema/1.0"}
    res = requests.get(url, headers=headers).json()
    pages = res.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        if "thumbnail" in page:
            return page["thumbnail"]["source"]
    return None

print("Brad Pitt:", get_image("Brad Pitt"))
print("Christopher Nolan:", get_image("Christopher Nolan"))
print("Denis Villeneuve:", get_image("Denis Villeneuve"))
