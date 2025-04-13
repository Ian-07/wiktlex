import json
import re
from unidecode import unidecode

wordlist_name = input("Enter wordlist title (leave blank for default \'wordlist\'): ")
old_wordlist_filename = input("OPTIONAL: enter full filename of old wordlist for comparison (leave blank to skip): ")

if wordlist_name == '':
    wordlist_name = "wordlist"

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
print(f"Generating {wordlist_name}...")

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
print(f"Outputting to {wordlist_name}.txt, {wordlist_name}_defs.txt, and {wordlist_name}_status.txt...")

wordlist = open(f"{wordlist_name}.txt", "w")
wordlist_defs = open(f"{wordlist_name}_defs.txt", "w", encoding="UTF-8")
wordlist_status = open(f"{wordlist_name}_status.txt", "w")

for word in sorted(list(words.keys())):
    wordlist.write(word + "\n")
    # current zyzzyva limits input lines to 640 characters, and anything longer than this leads to some funky behavior
    # hopefully, a future version will increase this limit, or at least improve the handling of long definitions
    wordlist_defs.write(f"{word} {" / ".join(words[word])}{" - also " + ", ".join(sorted(alts[word])) if word in alts else ""}"[:629] + "\n")

# cleaned-up version of statuses.txt, since some statuses might have been overridden
for md5 in sorted(list(statuses.keys())):
    wordlist_status.write(f"{md5} {statuses[md5]}\n")

wordlist.close()
wordlist_defs.close()
wordlist_status.close()

if old_wordlist_filename != '':
    print(f"Outputting additions and removals to {wordlist_name}_additions.txt and {wordlist_name}_removals.txt...")
    old_wordlist = open(f"{old_wordlist_filename}", "r")
    wordlist_additions = open(f"{wordlist_name}_additions.txt", "w")
    wordlist_removals = open(f"{wordlist_name}_removals.txt", "w")

    old_words = set(old_wordlist.read().split("\n"))
    new_words = set(words.keys())

    if "" in old_words:
        old_words.remove("")

    additions = [new_word for new_word in new_words if new_word not in old_words]
    removals = [old_word for old_word in old_words if old_word not in new_words]

    for word in sorted(additions, key=lambda x: (len(x), x)):
        wordlist_additions.write(word + "\n")

    for word in sorted(removals, key=lambda x: (len(x), x)):
        wordlist_removals.write(word + "\n")

    wordlist_additions.close()
    wordlist_removals.close()