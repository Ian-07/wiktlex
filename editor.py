from flask import Flask, render_template, request, redirect, url_for
import json
import re
from unidecode import unidecode

max_n = 1000

print("Reading headwords.txt...")

headwords = json.loads(open("headwords.txt", "r", encoding="UTF-8").read())

min_headword_length = min([len(headword) for headword in headwords])
max_headword_length = max([len(headword) for headword in headwords])

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
        else:
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
        return render_template("home.html", min_headword_length=min_headword_length, max_headword_length=max_headword_length, pos=sorted(list(pos)), max_n=max_n)

    if request.method == "POST":
        params = []

        for param in ["word", "minlength", "maxlength", "pos", "tag", "wordregex", "defregex",  "family", "unsure", "accepted", "rejected", "n", "offset", "sortbylength"]:
            if param in request.form:
                value = request.form[param]

                if value != "" and (param != "minlength" or int(value) > min_headword_length) and (param != "maxlength" or int(value) < max_headword_length) and (param == "word" or request.form["word"] == ""):
                    params.append(f"{param}={request.form[param]}")

        return redirect(f"{url_for("edit")}?{"&".join(params)}")

# checks whether definition contains
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
        words = []
        words_data = {}

        if "word" in request.args:
            word = unidecode(request.args.get("word")).upper()

            if word in headwords:
                words = [unidecode(word).upper()]

            n = 0
            offset = 0
            total_matches = 0
        else:
            matches = []

            for headword in headwords:
                match = True

                if match and "minlength" in request.args:
                    minlength = int(request.args.get("minlength"))

                    if len(headword) < minlength:
                        match = False

                if match and "maxlength" in request.args:
                    maxlength = int(request.args.get("maxlength"))

                    if len(headword) > maxlength:
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

            total_matches = len(matches)
            words = sorted_matches[offset:offset+n]

        for headword in words:
            # list of inflections to check for in the text of the definition; if they're there, deprioritize it to make it easier to choose definitions that make sense on their own
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

            # sort by whether it has self-reference, then by number of inflections, then by number of capital letters
            senses_sorted = sorted(headwords[headword], key=lambda x: (has_self_reference(unidecode(x["gloss"]).upper(), inflections), -len(list(set([unidecode(form).upper() for form in x["forms"] if unidecode(form).upper().isalpha()]))), sum(1 for c in x["word"] if c.isupper())))

            words_data[headword] = senses_sorted

        args_str = "?" + "&".join([f"{k}={v}" for k, v in request.args.items()])

        return render_template("edit.html", min=min, max=max, n=n, offset=offset, total_matches=total_matches, args_str=args_str, words=words_data, redundant_senses=redundant_senses, get_status=get_status, list_forms=lambda x: ",".join(set([unidecode(x["word"]).upper()] + [unidecode(i).upper() for i in x["forms"] if unidecode(i).upper().isalpha()])))

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

    for headword in headwords:
        if len(headword) not in total:
            accepted[len(headword)] = 0
            rejected[len(headword)] = 0
            unsure[len(headword)] = 0
            pending[len(headword)] = 0
            total[len(headword)] = 0

        total[len(headword)] += 1

        if overall_status[headword] == "+":
            accepted[len(headword)] += 1
        elif overall_status[headword] == "-":
            rejected[len(headword)] += 1
        elif overall_status[headword] == "?":
            unsure[len(headword)] += 1
        elif overall_status[headword] == ".":
            pending[len(headword)] += 1

    lengths = sorted(total.keys()) + ["Total"]

    accepted["Total"] = sum(accepted.values())
    rejected["Total"] = sum(rejected.values())
    unsure["Total"] = sum(unsure.values())
    pending["Total"] = sum(pending.values())
    total["Total"] = sum(total.values())

    data = {}

    for length in lengths:
        data[length] = (accepted[length], rejected[length], unsure[length], pending[length], total[length], (accepted[length] + rejected[length]) / total[length])

    return render_template("stats.html", data=data)

if __name__ == "__main__":
    app.run()