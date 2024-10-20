import json
import re
from unidecode import unidecode

print("Reading headwords.txt...")

headwords = json.loads(open("headwords.txt", "r", encoding="UTF-8").read())

print("Done.")
print("Reading statuses.txt...")

statuses_text = open("statuses.txt", "r").read().split("\n")
statuses = {}

for line in statuses_text:
    if len(line) == 34:
        (md5, status) = line.split(" ")
        statuses[md5] = status

print("Done.")
print("Generating wordlist...")

words = {}
alts = {}

def add_def(word, definition):
    if word not in words:
        words[word] = []

    words[word].append(definition)

def add_alt(word, alt):
    if word != alt:
        if word not in alts:
            alts[word] = set()

        alts[word].add(alt)

for headword in headwords:
    for sense in headwords[headword]:
        if sense["md5"] in statuses and statuses[sense["md5"]] == "+":
            add_def(headword, sense["def"])

            for form in sense["forms"]:
                form_upper = unidecode(form).upper()

                if form_upper != headword and form_upper.isalpha():
                    add_def(form_upper, f"{headword}: {re.sub(r"\[(.*?) .*?\]$", "[\\1]", sense["def"])}")

            if "alt" in sense:
                alt_headword = unidecode(sense["alt"]).upper()

                if alt_headword.isalpha():
                    add_alt(alt_headword, headword)

print("Done.")
print("Outputting to wordlist.txt, wordlist_defs.txt, and wordlist_status.txt...")

wordlist = open("wordlist.txt", "w")
wordlist_defs = open("wordlist_defs.txt", "w", encoding="UTF-8")
wordlist_status = open("wordlist_status.txt", "w")

for word in sorted(list(words.keys())):
    wordlist.write(word + "\n")
    wordlist_defs.write(f"{word} {" / ".join(words[word])}{" - also " + ", ".join(sorted(alts[word])) if word in alts else ""}\n")

# cleaned-up version of statuses.txt, since some statuses might have been overridden
for md5 in sorted(list(statuses.keys())):
    wordlist_status.write(f"{md5} {statuses[md5]}\n")

wordlist.close()
wordlist_defs.close()
wordlist_status.close()