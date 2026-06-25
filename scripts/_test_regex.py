def clean_think(text):
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    elif "<think>" in text:
        text = text.replace("<think>", "").strip()
    return text

s1 = "<think> I should write a story </think> [Setting: Earth] The story starts..."
s2 = "<think> I forgot to close the tag... [Setting: Mars] The story starts..."
print(clean_think(s1))
print(clean_think(s2))
