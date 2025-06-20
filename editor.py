from flask import Flask, render_template, request, redirect, send_file, url_for
import hashlib
import io
import json
import re
from unidecode import unidecode

max_n = 1000
uploaded_wordlists = {}

print("Reading headwords.json...")

headwords = json.loads(open("headwords.json", "r", encoding="UTF-8").read())

min_headword_length = min([len(headword) for headword in headwords])
max_headword_length = max([len(headword) for headword in headwords])
min_senses = min([len(headwords[headword]) for headword in headwords])
max_senses = max([len(headwords[headword]) for headword in headwords])

print("Done.")
print("Generating list of parts of speech...")

pos = set()

for headword in headwords:
    for sense in headwords[headword]:
        pos.add(sense["pos"])

print("Done.")
print("Reading statuses.txt...")

statuses_text = open("statuses.txt", "r").read().split("\n")
statuses = {}

for line in statuses_text:
    if len(line) == 34:
        (md5, status) = line.split(" ")

        if status != ".":
            statuses[md5] = status
        elif md5 in statuses:
            del statuses[md5]

print("Done.")
print("Determining overall status for each headword...")

overall_status = {}
redundant_senses = {}

def update_status(headword):
    redundant_senses[headword] = []

    accepted_forms = set()

    for sense in headwords[headword]:
        if sense["md5"] in statuses and statuses[sense["md5"]] == "+":
            for form in [headword] + sense["forms"]:
                inflected_headword = unidecode(form).upper()

                if inflected_headword.isalpha():
                    accepted_forms.add(inflected_headword)

    for sense in headwords[headword]:
        if sense["md5"] not in statuses:
            redundant = True

            for form in [headword] + sense["forms"]:
                inflected_headword = unidecode(form).upper()

                if inflected_headword.isalpha() and inflected_headword not in accepted_forms:
                    redundant = False

            if redundant:
                redundant_senses[headword].append(sense)

    status_list = []

    for sense in headwords[headword]:
        if sense["md5"] not in statuses:
            if sense in redundant_senses[headword]:
                status_list.append("/")
            else:
                status_list.append(".")
        elif sense["md5"] in statuses:
            status_list.append(statuses[sense["md5"]])

    # prioritize highlight pending senses first, then unsure, then return accepted if at least one sense is accepted
    for char in ".?+-":
        if char in status_list:
            overall_status[headword] = char
            break

for headword in headwords:
    update_status(headword)

print("Done.")
print("Loading Flask app...")

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        return render_template("home.html", min_headword_length=min_headword_length, max_headword_length=max_headword_length, min_senses=min_senses, max_senses=max_senses, pos=sorted(list(pos)), max_n=max_n)

    if request.method == "POST":
        params = []

        if request.files["wordlist"].filename != '':
            raw_wordlist = str(request.files["wordlist"].read())[2:-1]
            wordlist = set()

            for line in raw_wordlist.split("\\r\\n"):
                word = unidecode(line.split(" ")[0]).upper()

                if len(word) >= 0 and word.isupper() and word not in wordlist:
                    wordlist.add(word)

            digest = hashlib.md5(str(wordlist).encode("UTF-8")).hexdigest()
            uploaded_wordlists[digest] = wordlist
            params.append(f"wordlist={digest}")

        for param in ["word", "minlength", "maxlength", "minsenses", "maxsenses", "color", "selfref", "pos", "tag", "wordregex", "formregex", "defregex", "family", "unsure", "accepted", "rejected", "n", "offset", "sortbylength", "savetofile"]:
            if param in request.form:
                value = request.form[param]

                if value != "" and (param != "minlength" or int(value) > min_headword_length) and (param != "maxlength" or int(value) < max_headword_length) and (param != "minsenses" or int(value) > min_senses) and (param != "maxsenses" or int(value) < max_senses) and (param == "word" or request.form["word"] == ""):
                    params.append(f"{param}={request.form[param]}")

        return redirect(f"{url_for("edit")}?{"&".join(params)}")

# returns list of all inflections of all senses of a headword, plus "this", "these", and "such", for use in checking for self-references in the definition
def list_all_selfref_words(headword):
    inflections = set()

    # these sometimes lead to false positives, but whatever
    inflections.add("THIS")
    inflections.add("THESE")
    inflections.add("SUCH")

    inflections.add(headword)

    for sense in headwords[headword]:
        for form in sense["forms"]:
            form_unidecoded = unidecode(form).upper()

            if form_unidecoded.isalpha():
                inflections.add(form_unidecoded)

    return inflections

# checks whether definition contains the word itself, or the words "this", "these", or "such"
def has_self_reference(definition, inflections):
    split_definition = re.findall(r"\b\w+\b", definition)

    for inflection in inflections:
        if inflection in split_definition:
            return True

    return False

def get_status(headword, sense):
    if sense["md5"] in statuses:
        return statuses[sense["md5"]]
    elif sense in redundant_senses[headword]:
        return "/"
    else:
        return "."

@app.route("/edit", methods=["GET", "POST"])
def edit():
    if request.method == "GET":
        msg = ""

        words = []
        words_data = {}

        if "word" in request.args:
            word = unidecode(request.args.get("word")).upper()

            if word in headwords:
                words = [unidecode(word).upper()]
            else:
                msg = "No results found."

            n = 0
            offset = 0
            total_matches = 0
        else:
            matches = []

            for headword in headwords:
                match = True

                if match and "wordlist" in request.args:
                    md5 = request.args.get("wordlist")

                    if md5 in uploaded_wordlists:
                        wordlist = uploaded_wordlists[md5]

                        if headword not in wordlist:
                            match = False
                    else:
                        msg = "Could not find uploaded wordlist. Try reuploading it."

                if match and "minlength" in request.args:
                    minlength = int(request.args.get("minlength"))

                    if len(headword) < minlength:
                        match = False

                if match and "maxlength" in request.args:
                    maxlength = int(request.args.get("maxlength"))

                    if len(headword) > maxlength:
                        match = False

                if match and "minsenses" in request.args:
                    minsenses = int(request.args.get("minsenses"))

                    if len(headwords[headword]) < minsenses:
                        match = False

                if match and "maxsenses" in request.args:
                    maxsenses = int(request.args.get("maxsenses"))

                    if len(headwords[headword]) > maxsenses:
                        match = False

                if match and "color" in request.args:
                    color = request.args["color"]
                    color_found = False

                    for sense in headwords[headword]:
                        def_lower = sense["def"].lower()

                        if color == "green" and "alt" in sense:
                            color_found = True

                        if color == "yellow" and ("misspelling" in def_lower or "misconstruction" in def_lower or "eggcorn" in def_lower or "obsolete typography" in def_lower):
                            color_found = True

                        if color == "blue" and ("abbreviation" in def_lower or "acronym" in def_lower or "initialism" in def_lower):
                            color_found = True

                        if color == "purple" and sense["pos"] == "name":
                            color_found = True

                        if color == "pink" and "TRANSLINGUAL" in sense["tags"]:
                            color_found = True

                        if color in ["gray", "grey"] and "AUTOGEN" in sense["tags"]:
                            color_found = True

                        if color == "red" and ("derogatory" in sense["tags"] or "offensive" in sense["tags"] or "slur" in sense["tags"]):
                            color_found = True

                    if not color_found:
                        match = False

                if match and "selfref" in request.args:
                    inflections = list_all_selfref_words(headword)
                    selfref_found = False

                    for sense in headwords[headword]:
                        if has_self_reference(unidecode(sense["gloss"]).upper(), inflections):
                            selfref_found = True
                            break

                    if not selfref_found:
                        match = False

                if match and "pos" in request.args:
                    pos = request.args.get("pos")
                    pos_found = False

                    for sense in headwords[headword]:
                        if sense["pos"] == pos:
                            pos_found = True
                            break

                    if not pos_found:
                        match = False

                if match and "tag" in request.args:
                    tag = request.args.get("tag")
                    tag_found = False

                    for sense in headwords[headword]:
                        if tag in sense["tags"]:
                            tag_found = True
                            break

                    if not tag_found:
                        match = False

                if match and "wordregex" in request.args:
                    wordregex = request.args.get("wordregex")

                    if not bool(re.search(wordregex, headword)):
                        match = False

                if match and "formregex" in request.args:
                    defregex = request.args.get("formregex")
                    regex_match_found = False

                    for sense in headwords[headword]:
                        if bool(re.search(defregex, sense["word"])):
                            regex_match_found = True
                            break

                    if not regex_match_found:
                        match = False

                if match and "defregex" in request.args:
                    defregex = request.args.get("defregex")
                    regex_match_found = False

                    for sense in headwords[headword]:
                        if bool(re.search(defregex, sense["def"])):
                            regex_match_found = True
                            break

                    if not regex_match_found:
                        match = False

                if match and "family" in request.args:
                    tag_found = False

                    for sense in headwords[headword]:
                        tag_found = False

                        for tag in sense["tags"]:
                            if tag in ["vulgar", "derogatory", "offensive", "slur"]:
                                tag_found = True
                                break

                        if tag_found:
                            break

                    if tag_found:
                        match = False

                if match and overall_status[headword] != "." and (("unsure" not in request.args and overall_status[headword] == "?") or ("accepted" not in request.args and overall_status[headword] == "+") or ("rejected" not in request.args and overall_status[headword] == "-")):
                    match = False

                if match:
                    matches.append(headword)

            if "n" in request.args:
                n = int(request.args.get("n"))
            else:
                n = max_n

            if "offset" in request.args:
                offset = max(int(request.args.get("offset")), 0)
            else:
                offset = 0

            if "sortbylength" in request.args:
                sorted_matches = sorted(matches, key=lambda x: (len(x), x))
            else:
                sorted_matches = sorted(matches)

            if "savetofile" in request.args:
                output_text = "\n".join(sorted_matches).encode("UTF-8")
                output_filename = f"{hashlib.md5(output_text).hexdigest()}.txt"
                output_data = io.BytesIO()
                output_data.write(bytes(output_text))
                output_data.seek(0)

                return send_file(output_data, download_name=output_filename, as_attachment=True)

            total_matches = len(matches)
            words = sorted_matches[offset:offset+n]

            if total_matches == 0 and msg == "":
                msg = "No results found."

        for headword in words:
            # list of inflections to check for in the text of the definition; if they're there, deprioritize it to make it easier to choose definitions that make sense on their own
            inflections = list_all_selfref_words(headword)

            # sort by whether it has self-reference, then by number of inflections, then by number of capital letters
            senses_sorted = sorted(headwords[headword], key=lambda x: (has_self_reference(unidecode(x["gloss"]).upper(), inflections), -len(list(set([unidecode(form).upper() for form in x["forms"] if unidecode(form).upper().isalpha()]))), sum(1 for c in x["word"] if c.isupper())))

            words_data[headword] = senses_sorted

        args_str = "?" + "&".join([f"{k}={v}" for k, v in request.args.items()])

        return render_template("edit.html", msg=msg, min=min, max=max, n=n, offset=offset, total_matches=total_matches, args_str=args_str, words=words_data, redundant_senses=redundant_senses, get_status=get_status, list_forms=lambda x: ",".join(set([unidecode(x["word"]).upper()] + [unidecode(i).upper() for i in x["forms"] if unidecode(i).upper().isalpha()])))

    if request.method == "POST":
        statuses_out = open("statuses.txt", "a")

        words_to_update = set()

        for k, v in request.form.items():
            (word, md5) = k.split(" ")
            status = v

            if (status != "." or md5 in statuses) and (md5 not in statuses or status != statuses[md5]):
                if status != ".":
                    statuses[md5] = status
                else:
                    del statuses[md5]

                words_to_update.add(word)
                statuses_out.write(f"{md5} {status}\n")

        statuses_out.close()

        for headword in words_to_update:
            update_status(headword)

        args_str = "?" + "&".join([f"{k}={v}" for k, v in request.args.items()])

        return redirect(url_for("edit") + args_str)

@app.route("/stats")
def stats():
    accepted = {}
    rejected = {}
    unsure = {}
    pending = {}
    total = {}

    statuses = [accepted, rejected, unsure, pending, total]

    for headword in headwords:
        length = len(headword)
        letter = headword[0]

        if length not in total:
            for status in statuses:
                status[length] = 0

        if letter not in total:
            for status in statuses:
                status[letter] = 0

        total[length] += 1
        total[letter] += 1

        if overall_status[headword] == "+":
            accepted[length] += 1
            accepted[letter] += 1
        elif overall_status[headword] == "-":
            rejected[length] += 1
            rejected[letter] += 1
        elif overall_status[headword] == "?":
            unsure[length] += 1
            unsure[letter] += 1
        elif overall_status[headword] == ".":
            pending[length] += 1
            pending[letter] += 1

    lengths = sorted([i for i in total.keys() if type(i) is int]) + ["Total"]
    letters = sorted([i for i in total.keys() if type(i) is str]) + ["Total"]

    for status in statuses:
        status["Total"] = sum([v for k, v in status.items() if type(k) is int])

    length_data = {}
    letter_data = {}

    for length in lengths:
        length_data[length] = (accepted[length], rejected[length], unsure[length], pending[length], total[length], (accepted[length] + rejected[length]) / total[length])

    for letter in letters:
        letter_data[letter] = (accepted[letter], rejected[letter], unsure[letter], pending[letter], total[letter], (accepted[letter] + rejected[letter]) / total[letter])

    return render_template("stats.html", length_data=length_data, letter_data=letter_data)

if __name__ == "__main__":
    app.run()