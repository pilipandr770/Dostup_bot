with open("app/bot.py", "r") as file:
    content = file.read().replace("\t", "    ")

with open("app/bot.py", "w") as file:
    file.write(content)
