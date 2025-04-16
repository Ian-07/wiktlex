import copy
import hashlib
import json
import re
import time
from unidecode import unidecode

print("WARNING: This script will overwrite headwords.txt and statuses.txt!")

raw_filename = input("Enter filename for raw wiktextract data (leave blank for default 'raw-wiktextract-data.jsonl'): ")

run_bonus_scripts = input("Run bonus searches for potentially missing words? (type anything for yes, leave blank for no): ") != ""

if raw_filename == '':
    raw_filename = "raw-wiktextract-data.jsonl"

raw = open(raw_filename, "r", encoding="UTF-8")
print("Parsing %s..." % raw_filename)

entries = []
n = 0
last_message = time.time()
for line in raw:
    entry = json.loads(line)

    if "lang" in entry.keys() and entry["lang"] in ["English", "Translingual"]:
        entries.append(entry)

    n += 1
    if time.time() - last_message >= 10:
        last_message = time.time()
        print("Parsing %s... (%d lines parsed)" % (raw_filename, n))

print("Done. %d lines parsed." % n)

if run_bonus_scripts:
    print("BONUS: initiating bonus scripts...")

    entry_words = {}

    for entry in entries:
        entry_word = entry["word"]

        if entry_word not in entry_words:
            entry_words[entry_word] = []

        entry_words[entry_word].append(entry)

    # multiword: generates a list of words that exist as part of multiword terms but don't have standalone entries
    # for example, as of writing "EC" only appears as part of the phrase "home ec"
    # not all of these actually warrant pages; in this case, it's clear that EC is a clipping of "economics", but DEJA and VU probably wouldn't
    print("BONUS: finding words which are part of multiword terms but do not have standalone entries...")

    multiword_out = open("bonus_multiword.txt", "w", encoding="UTF-8")
    multiword_lines = []

    for entry_word in entry_words:
        words = entry_word.split(" ")

        for single_word in words:
            if single_word not in entry_words.keys() and unidecode(single_word).isalpha():
                multiword_lines.append(f"{unidecode(single_word).upper()} (\"{single_word}\" from \"{entry_word}\")\n")

    for line in sorted(multiword_lines):
        multiword_out.write(line)

    print("Outputted multiword-only words to bonus_multiword.txt.")

    # hyphenated: generates a list of words which have hyphens in them but where the non-?hyphenated form isn't on wiktionary
    # again, make sure these are actually attested before adding to wiktionary
    print("BONUS: finding entries which are hyphenated but do not have hyphenated forms...")

    hyphenated_out = open("bonus_hyphenated.txt", "w", encoding="UTF-8")
    hyphenated_lines = []

    for entry_word in entry_words:
        no_hyphens = entry_word.replace("-", "")

        if entry_word[0] != "-" and entry_word[-1] != "-" and no_hyphens not in entry_words.keys() and unidecode(no_hyphens).isalpha():
            hyphenated_lines.append(f"{unidecode(no_hyphens).upper()} (\"{no_hyphens}\" from \"{entry_word}\")\n")

    for line in sorted(hyphenated_lines):
        hyphenated_out.write(line)

    print("Outputted hyphenated-only entries to bonus_hyphenated.txt.")

    # redlinks: generates a list of redlinks found within the raw wiktextract data, e.g. alternate forms that are listed but don't have actual entries yet
    print("BONUS: finding redlinks...")

    redlinks_out = open("bonus_redlinks.txt", "w", encoding="UTF-8")
    redlinks_lines = []

    # list of keys which could contain links to other entries
    linkage_keys = ["synonyms", "antonyms", "hypernyms", "derived words", "holonyms", "meronyms", "derived", "related", "coordinate_terms"]

    for entry_word in entry_words:
        for entry in entry_words[entry_word]:
            for linkage_key in linkage_keys:
                if linkage_key in entry.keys():
                    for linkage in entry[linkage_key]:
                        linked_entry = linkage["word"]

                        if linked_entry not in entry_words.keys() and unidecode(linked_entry).replace("-", "").isalpha():
                            redlinks_lines.append(f"{unidecode(linked_entry).upper()} (\"{linked_entry}\" from \"{entry_word}\")\n")

            if "forms" in entry.keys():
                for form in entry["forms"]:
                    if "tags" in form and "alternative" in form["tags"]:
                        linked_entry = form["form"]

                        if linked_entry not in entry_words.keys() and unidecode(linked_entry).replace("-", "").isalpha():
                            redlinks_lines.append(f"{unidecode(linked_entry).upper()} (\"{linked_entry}\" from \"{entry_word}\")\n")

            if "senses" in entry.keys():
                for sense in entry["senses"]:
                    if "links" in sense.keys():
                        for link in sense["links"]:
                            linked_entry = link[1].split("#")[0]

                            if linked_entry not in entry_words.keys() and unidecode(linked_entry).replace("-", "").isalpha():
                                redlinks_lines.append(f"{unidecode(linked_entry).upper()} (\"{linked_entry}\" from \"{entry_word}\")\n")

    for line in sorted(redlinks_lines):
        redlinks_out.write(line)

    print("Outputted redlinks to bonus_redlinks.txt.")

print("Extracting and organizing data from English/Translingual entries...")

headwords = {}
headwords_out = open("headwords.txt", "w", encoding="UTF-8")
statuses_out = open("statuses.txt", "w", encoding="UTF-8")

pos_abbr = {
    "contraction": "contr",
    "intj": "interj",
    "name": "n",
    "noun": "n",
    "num": "n",
    "prep_phrase": "prep phrase",
    "verb": "v"
}

def get_pos_abbr(s):
    if s in pos_abbr.keys():
        return pos_abbr[s]
    else:
        return s

n = 0
last_message = time.time()
for entry in entries:
    if "senses" in entry.keys() and "pos" in entry.keys():
        headword = unidecode(entry["word"]).upper()

        if len(headword) >= 1:
            if headword not in headwords:
                headwords[headword] = []

            for sense in entry["senses"]:
                # subdefinitions actually include glosses for all levels of the definition so handling that is a bit awkward
                if "glosses" in sense.keys():
                    glosses = sense["glosses"]
                else:
                    glosses = [""]

                if "\n" not in glosses[0]: # weird case where the list of derived/related terms is misinterpreted as a definition
                    for gloss in glosses:
                        sense_data = {}
                        sense_data["word"] = entry["word"] # retains original capitalization and/or diacritics
                        sense_data["gloss"] = gloss.replace("\n", " ")
                        sense_data["pos"] = entry["pos"]
                        sense_data["forms"] = []
                        sense_data["tags"] = []

                        if "forms" in entry.keys():
                            for form in entry["forms"]:
                                if ("tags" not in form or ("abbreviation" not in form["tags"] and "alternative" not in form["tags"] and "symbol" not in form["tags"] and ("infinitive" not in form["tags"] or form["form"] != sense_data["word"]))) and form["form"] != "glossary" and form["form"] != "no-table-tags" and (sense_data["word"][-1] != "S" or form["form"][-1] != "s"):
                                    sense_data["forms"].append(form["form"])

                        if "qualifier" in sense.keys():
                            # addresses weird bug in wiktextract where the qualifier text gets duplicated when there's a semicolon
                            sense_data["tags"].append("; ".join(list(dict.fromkeys(sense["qualifier"].split("; ")))))

                        if "tags" in sense.keys():
                            sense_data["tags"] += sense["tags"]

                        if "raw_tags" in sense.keys():
                            sense_data["tags"] += sense["raw_tags"]

                        # to extract some additional topical tags that wouldn't otherwise be included in the definition
                        if "raw_glosses" in sense.keys():
                            for raw_gloss in sense["raw_glosses"]:
                                match = re.match(r"\(.*?\)", raw_gloss)

                                if match is not None:
                                    displayed_tags = match.group()[1:-1].split(", ")

                                    for tag in displayed_tags:
                                        if tag not in sense_data["tags"]:
                                            sense_data["tags"].append(tag)

                        if "uncountable" in sense_data["tags"] and "(countable)" in sense_data["gloss"]:
                            sense_data["tags"].remove("uncountable")

                        if entry["lang"] == "Translingual":
                            sense_data["tags"].append("TRANSLINGUAL")

                        # if a specific sense is marked as uncountable or not-comparable (and not merely "usually uncountable" or "countable and uncountable"), remove all inflections.
                        if (((entry["pos"] == "noun" or entry["pos"] == "name") and "uncountable" in sense_data["tags"] and "countable" not in sense_data["tags"]) or (entry["pos"] == "adj" and "not-comparable" in sense_data["tags"] and "comparable" not in sense_data["tags"])) and "usually" not in sense_data["tags"]:
                            sense_data["forms"] = []

                        # to prevent duplication of identical inflected forms (e.g. past and past participle for a verb)
                        sense_data["forms"] = list(dict.fromkeys(sense_data["forms"]))

                        # to prevent duplication of higher-level definitions while still having one copy of them
                        definition_already_exists = False

                        sense_data_json = json.dumps(sense_data)
                        for existing_sense in headwords[headword]:
                            if json.dumps(existing_sense) == sense_data_json:
                                definition_already_exists = True

                        if not definition_already_exists:
                            headwords[headword].append(sense_data)

    n += 1
    if time.time() - last_message >= 10:
        last_message = time.time()
        print(f"Extracting and organizing data from English/Translingual entries... ({n}/{len(entries)} entries done)")

print(f"{n} entries done.")
print("Expanding alternative forms...")

if run_bonus_scripts:
    print("BONUS: finding orphaned alternative forms...")

    orphans_out = open("bonus_orphans.txt", "w", encoding="UTF-8")
    orphans_lines = []

# need to extract the word that each sense is an alternative form of
alt_patterns = [r"Abbreviation of (.*?)\.?$", r"abstract noun of (.*?)\.?$", r"Acronym of (.*?)\.?$", r"active participle of (.*?)\.?$", r"agent noun of (.*?)\.?$", r"Alternative letter-case form of (.*?)\.?$", r"Alternative form of (.*?)\.?$", r"plural of .*? \(alternative form of (.*?)\)\.?$", r"Alternative reconstruction of (.*?)\.?$", r"Alternative spelling of (.*?)\.?$", r"alternative typography of (.*?)\.?$", r"Aphetic form of (.*?)\.?$", r"Apocopic form of (.*?)\.?$", r"Archaic form of (.*?)\.?$", r"Archaic form of (.*?)\.?$", r"Archaic spelling of (.*?)\.?$", r"Aspirate mutation of (.*?)\.?$", r"attributive form of (.*?)\.?$", r"Augmentative of (.*?)\.?$", r"broad form of (.*?)\.?$", r"causative of (.*?)\.?$", r"Clipping of (.*?)\.?$", r"Combining form of (.*?)\.?$", r"comparative degree of (.*?)\.?$", r"comparative form of (.*?)\.?$", r"construed with (.*?)\.?$", r"Contraction of (.*?)\.?$", r"Dated form of (.*?)\.?$", r"Dated spelling of (.*?)\.?$", r"Deliberate misspelling of (.*?)\.?$", r"diminutive of (.*?)\.?$", r"Eclipsed form of (.*?)\.?$", r"Eggcorn of (.*?)\.?$", r"Ellipsis of (.*?)\.?$", r"Elongated form of (.*?)\.?$", r"endearing diminutive of (.*?)\.?$", r"endearing form of (.*?)\.?$", r"Euphemistic form of (.*?)\.?$", r"Eye dialect spelling of (.*?)\.?$", r"female equivalent of (.*?)\.?$", r"feminine of (.*?)\.?$", r"feminine plural of (.*?)\.?$", r"feminine plural of the past participle of (.*?)\.?$", r"feminine singular of (.*?)\.?$", r"feminine singular of the past participle of (.*?)\.?$", r"Former name of (.*?)\.?$", r"frequentative of (.*?)\.?$", r"gerund of (.*?)\.?$", r"h-prothesized form of (.*?)\.?$", r"Hard mutation of (.*?)\.?$", r"harmonic variant of (.*?)\.?$", r"Honorific alternative letter-case form of (.*?), sometimes used when referring to God or another important figure who is understood from context\.?$", r"imperfective form of (.*?)\.?$", r"Informal form of (.*?)\.?$", r"Informal spelling of (.*?)\.?$", r"Initialism of (.*?)\.?$", r"iterative of (.*?)\.?$", r"Lenited form of (.*?)\.?$", r"literary form of (.*?)\.?$", r"masculine equivalent of (.*?)\.?$", r"masculine of (.*?)\.?$", r"masculine plural of (.*?)\.?$", r"masculine plural of the past participle of (.*?)\.?$", r"medieval spelling of (.*?)\.?$", r"men's speech form of (.*?)\.?$", r"Misconstruction of (.*?)\.?$", r"Misromanization of (.*?)\.?$", r"Misspelling of (.*?)\.?$", r"Mixed mutation of (.*?)\.?$", r"Nasal mutation of (.*?)\.?$", r"negative form of (.*?)\.?$", r"neuter plural of (.*?)\.?$", r"neuter singular of (.*?)\.?$", r"neuter singular of the past participle of (.*?)\.?$", r"Nomen sacrum form of (.*?)\.?$", r"nominalization of (.*?)\.?$", r"Nonstandard form of (.*?)\.?$", r"Nonstandard spelling of (.*?)\.?$", r"nuqtaless form of (.*?)\.?$", r"Obsolete form of (.*?)\.?$", r"Obsolete spelling of (.*?)\.?$", r"obsolete typography of (.*?)\.?$", r"participle of (.*?)\.?$", r"(deprecated template usage) passive of (.*?)\.?$", r"passive participle of (.*?)\.?$", r"of the past participle of (.*?)\.?$", r"past participle of (.*?)\.?$", r"Pejorative of (.*?)\.?$", r"perfective form of (.*?)\.?$", r"plural of (.*?)\.?$", r"present participle and gerund of (.*?)\.?$", r"present participle of (.*?)\.?$", r"Pronunciation spelling of (.*?)\.?$", r"Pronunciation variant of (.*?)\.?$", r"Rare form of (.*?)\.?$", r"Rare spelling of (.*?)\.?$", r"reflexive of (.*?)\.?$", r"Romanization of (.*?)\.?$", r"Scribal abbreviation of (.*?)\.?$", r"Short for (.*?)\.?$", r"simple past of (.*?)\.?$", r"singular of (.*?)\.?$", r"slender form of (.*?)\.?$", r"Soft mutation of (.*?)\.?$", r"Standard form of (.*?)\.?$", r"Standard spelling of (.*?)\.?$", r"superlative degree of (.*?)\.?$", r"superlative form of (.*?)\.?$", r"Superseded spelling of (.*?)\.?$", r"Syncopic form of (.*?)\.?$", r"Synonym of (.*?)\.?$", r"t-prothesized form of (.*?)\.?$", r"third-person singular simple present indicative of (.*?)\.?$", r"Uncommon form of (.*?)\.?$", r"Uncommon spelling of (.*?)\.?$", r"verbal noun of (.*?)\.?$", r".*? spelling of (.*?)\.?$"]

# if an alternative form, make copies of sense with parentheticals for each definition of the word
# sometimes captures too much, but if so, it just won't copy the sense since there's no definition associated with the captured string
headwords_started = {}
headwords_expanded = {}

# returns whether inputted list has adjective/adverb forms ending in -er or -est
def has_er_est_form(l):
    er_est_found = False

    for adj_form in l:
        adj_form_unidecoded = unidecode(adj_form).upper()

        if adj_form_unidecoded.isalpha() and len(adj_form_unidecoded) >= 3 and (
                adj_form_unidecoded[-2:] == "ER" or adj_form_unidecoded[-3:] == "EST"):
            er_est_found = True

    return er_est_found

def expand_alts(headword):
    # prevents infinite recursion
    headwords_started[headword] = True

    if headword not in headwords_expanded.keys():
        sense_copies = []

        for sense in headwords[headword]:
            for pattern in alt_patterns:
                match = re.match(pattern, sense["gloss"], flags=re.IGNORECASE)

                if match is not None:
                    match2 = re.match(r"(.*?)( \(|\.|;|:|,|!|\?|$)", match.group(1))

                    if match2 is not None:
                        alt = match2.group(1)
                        sense["alt"] = alt

                        alt_headword = unidecode(sense["alt"]).upper()

                        parent_sense_found = False

                        if alt_headword != headword:
                            # find all senses with matching capitalization as well as matching part of speech
                            if alt_headword in headwords:
                                if alt_headword not in headwords_started:
                                    expand_alts(alt_headword)

                                for alt_sense in headwords[alt_headword]:
                                    if alt_sense["word"] == sense["alt"] and get_pos_abbr(alt_sense["pos"]) == get_pos_abbr(sense["pos"]):
                                        sense_copy = copy.deepcopy(sense)
                                        sense_copy["gloss"] = sense["gloss"].replace(match.group(1), match2.group(1) + " (" + alt_sense["gloss"] + ")")

                                        # keep countability/comparability consistent between parent and child
                                        if (alt_sense["pos"] == "noun" or alt_sense["pos"] == "name") and "uncountable" in alt_sense["tags"] and "countable" not in alt_sense["tags"] and "usually" not in alt_sense["tags"] and ("uncountable" not in sense_copy["tags"] or "countable" in sense_copy["tags"]):
                                            sense_copy["tags"].append("uncountable")

                                            if "countable" in sense_copy["tags"]:
                                                sense_copy["tags"].remove("countable")

                                            sense_copy["forms"] = []

                                        if (alt_sense["pos"] == "noun" or alt_sense["pos"] == "name") and ("uncountable" not in alt_sense["tags"] or "countable" in alt_sense["tags"] or "usually" in alt_sense["tags"]) and "countable" not in sense_copy["tags"] and "uncountable" in sense_copy["tags"]:
                                            sense_copy["tags"].remove("uncountable")

                                        if (alt_sense["pos"] in ["adj", "adv"] and "not-comparable" in alt_sense["tags"] and "comparable" not in alt_sense["tags"]) and "usually" not in alt_sense["tags"] and ("not-comparable" not in sense_copy["tags"] or "comparable" in sense_copy["tags"]):
                                            sense_copy["tags"].append("not-comparable")

                                            if "comparable" in sense_copy["tags"]:
                                                sense_copy["tags"].remove("comparable")

                                            sense_copy["forms"] = []

                                        # look for adj/adv forms which are single words ending in -er or -est
                                        if alt_sense["pos"] in ["adj", "adv"] and has_er_est_form(alt_sense["forms"]):
                                            sense_copy["tags"].append("ALLOW ADJ AUTOGEN")

                                        for tag in ["vulgar", "derogatory", "offensive", "slur"]:
                                            if tag in alt_sense["tags"] and tag not in sense_copy["tags"]:
                                                sense_copy["tags"].append(tag)

                                        # if A is an alt of B which is an alt of C, set A's parent to C (if C is alpha)
                                        # this is so that the list of alternate forms in C's definition is more complete
                                        if "alt" in alt_sense and unidecode(alt_sense["alt"]).isalpha():
                                            sense_copy["alt"] = alt_sense["alt"]

                                        sense_copies.append(sense_copy)

                                        parent_sense_found = True

                        if run_bonus_scripts and not parent_sense_found and headword.isalpha() and alt_headword.isalpha() and headword != alt_headword:
                            orphans_lines.append(f"{headword} (parent {alt_headword})\n")

        for sense_copy in sense_copies:
            headwords[headword].append(sense_copy)

        headwords_expanded[headword] = True

n = 0
last_message = time.time()
for headword in headwords:
    expand_alts(headword)

    n += 1
    if time.time() - last_message >= 10:
        last_message = time.time()
        print(f"Expanding alternative forms... ({n}/{len(headwords)} headwords done)")

if run_bonus_scripts:
    for line in sorted(orphans_lines):
        orphans_out.write(line)

    print("Outputted orphaned alternative forms to bonus_orphans.txt.")

print("Done.")

# there are some entries on wiktionary that don't link to their inflected forms, so the inflections that aren't linked to will have to be verified separately; other than these, however, we can remove most of the inflected senses and allow them to be automatically added later based on the original entry
print("Purging most inflections...")

for headword in headwords:
    inflections = {}

    for sense in headwords[headword]:
        word = sense["word"]

        if word not in inflections:
            inflections[word] = (set())

        for form in sense["forms"]:
            inflections[word].add(form)

    for word in inflections:
        for inflection in inflections[word]:
            inflected_headword = unidecode(inflection).upper()

            if inflected_headword in headwords:
                for sense in headwords[inflected_headword]:
                    if "form-of" in sense["tags"] and word in sense["gloss"]:
                        sense["delete"] = True

for headword in headwords:
    for sense in list(headwords[headword]):
        if "delete" in sense.keys():
            headwords[headword].remove(sense)

print("Done.")
# the reason we didn't do this earlier is because some single-word entries relate back to multi-word entries, so we want to preserve their defs
print("Purging entries with non-alphabetical characters...")

for headword in list(headwords.keys()):
    if not headword.isalpha() or len(headwords[headword]) == 0:
        del headwords[headword]

print("Done.")
print("Automatically adding inflections for some words... (these can be rejected later)")

# warning: this will occasionally lead to some clearly nonsensical constructions that i can't be bothered to figure out how to automatically filter out, so just reject those when they pop up
for headword in headwords:
    # pluralizes the following types of senses:
    # "unknown or uncertain plurals" (does not have forms listed but also does not have "uncountable" tag)
    # "plural not attested" (has the "no-plural" tag)
    # any entries that use {{head|en|noun}} or {{head|en|verb}} directly and thus don't list inflections
    for sense in headwords[headword]:
        # please forgive me for this monstrosity
        if sense["pos"] in ["noun", "num"] and len(sense["forms"]) == 0 and (("countable" not in sense["tags"] and "uncountable" not in sense["tags"] and "form-of" not in sense["tags"] and "plural" not in sense["tags"]) or "no-plural" in sense["tags"]) and "plural" not in sense["gloss"]:
            if headword[-1] == "Y" and len(headword) >= 2 and headword[-2] not in "AEIOUY":
                plural = headword[:-1] + "IES"
            elif headword[-3:] == "SIS":
                plural = headword[:-2] + "ES"
            elif headword[-1] in "JSXZ" or headword[-2:] in ["SH", "ZH"] or headword[-3:] in ["NCH", "SCH", "TCH"] or headword[-4:] in ["EACH", "EECH", "OACH", "OUCH"]:
                plural = headword + "ES"
            else:
                plural = headword + "S"

            sense_copy = copy.deepcopy(sense)
            sense_copy["forms"].append(plural)
            sense_copy["tags"].append("AUTOGEN")
            headwords[headword].append(sense_copy)

        if sense["pos"] == "verb" and len(sense["forms"]) <= 2 and "form-of" not in sense["tags"]:
            s = None
            ing = None
            ed = None

            if headword[-1] == "Y" and len(headword) >= 2 and headword[-2] not in "AEIOUY":
                s = headword[:-1] + "IES"
                ing = headword + "ING"
                ed = headword[:-1] + "IED"
            elif headword[-1] == "E":
                ed = headword + "D"
                s = headword + "S"

                if len(headword) >= 2 and headword[-2] not in "AEIO":
                    ing = headword[:-1] + "ING"
                else:
                    ing = headword + "ING"
            elif len(headword) >= 2 and headword[-1] in "BCDFGKLMNPRSTV" and headword[-2] in "AEIOUY" and headword[-1] != headword[-2] and (len(headword) == 2 or headword[-2] != headword[-3]):
                if headword[-1] == "S":
                    s = headword + "SES"
                else:
                    s = headword + "S"

                ing = headword + headword[-1] + "ING"
                ed = headword + headword[-1] + "ED"
            elif headword[-1] in "JXZ" or headword[-2:] in ["SH", "ZH"] or headword[-3:] in ["NCH", "SCH", "TCH"] or headword[-4:] in ["EACH", "EECH", "OACH", "OUCH"]:
                s = headword + "ES"
                ing = headword + "ING"
                ed = headword + "ED"
            else:
                if headword[-1] == "S":
                    s = headword + "ES"
                else:
                    s = headword + "S"

                ing = headword + "ING"
                ed = headword + "ED"

            sense_copy = copy.deepcopy(sense)
            sense_copy["forms"].append(s)
            sense_copy["forms"].append(ing)
            sense_copy["forms"].append(ed)
            sense_copy["tags"].append("AUTOGEN")
            headwords[headword].append(sense_copy)

        if "ALLOW ADJ AUTOGEN" in sense["tags"] and not has_er_est_form(sense["forms"]) and "form-of" not in sense["tags"]:
            er = None
            est = None

            if headword[-1] == "Y" and len(headword) >= 2 and headword[-2:] == "EY":
                er = headword[:-2] + "IER"
                est = headword[:-2] + "IEST"
            elif headword[-1] == "Y" and len(headword) >= 2 and headword[-2] not in "AEIOUY":
                er = headword[:-1] + "IER"
                est = headword[:-1] + "IEST"
            elif headword[-1] == "E":
                er = headword + "R"
                est = headword + "ST"
            elif len(headword) >= 2 and headword[-1] in "BCDFGKLMNPRSTV" and headword[-2] in "AEIOUY" and headword[-1] != headword[-2] and (len(headword) == 2 or headword[-2] != headword[-3]):
                er = headword + headword[-1] + "ER"
                est = headword + headword[-1] + "EST"
            else:
                er = headword + "ER"
                est = headword + "EST"

            sense_copy = copy.deepcopy(sense)
            sense_copy["forms"].append(er)
            sense_copy["forms"].append(est)
            sense_copy["tags"].append("AUTOGEN")
            headwords[headword].append(sense_copy)

print("Done.")
print("Rendering senses...")

excluded_tags = {"abbreviation", "acronym", "adjective", "adverb", "adverbial", "agent", "ALLOW ADJ AUTOGEN", "alt-of", "alternative", "ambitransitive", "Anglicised", "anterior", "apocopic", "aspect", "attributive", "AUTOGEN", "auxiliary", "capitalized", "catenative", "causative", "character", "clipping", "comparable", "comparative", "comparative-only", "conjunctive", "contracted", "copulative", "countable", "dative", "defective", "definite", "definition", "deliberate", "demonstrative", "degree", "demonym", "determiner", "direct", "distal", "ditransitive", "duration", "ellipsis", "empty-gloss", "ergative", "error-lua-exec", "error-misspelling", "familiar", "feminine", "first-person", "focus", "form-of", "frequency", "g-person", "genitive", "gerund", "hard", "heading", "imperative-only", "imperfect", "impersonal", "in-compounds", "in-plural", "indeclinable", "indefinite", "indicative", "indirect", "initialism", "intensifier", "interrogative", "intransitive", "invariable", "irregular", "letter", "location", "lowercase", "manner", "masculine", "medial", "misconstruction", "misspelling", "modal", "morpheme", "negative", "neologism", "neuter", "no-comparative", "no-gloss", "no-past", "no-past-participle", "no-plural", "no-present-participle", "nominative", "not countable", "not comparable", "not-comparable", "noun-from-verb", "objective", "oblique", "participle", "passive", "perfect", "perfective", "personal", "phoneme", "phrase", "place", "plural", "plural-normally", "plural-only", "positive", "possessive", "predicative", "present", "pronoun", "pronunciation-spelling", "proper-noun", "proximal", "reciprocal", "reduplication", "reflexive", "relative", "romanization", "second-person", "sequence", "singular", "singular-only", "stative", "strict-sense", "subjective", "subjunctive", "substantive", "superlative", "third-person", "time", "transitive", "TRANSLINGUAL", "uncountable", "universal", "uppercase", "usually uncountable", "variant", "verb", "vocative", "with-infinitive"}

for headword in headwords:
    for sense in headwords[headword]:
        definition = ""

        tags_to_include = []

        for tag in sense["tags"]:
            if tag not in excluded_tags:
                tags_to_include.append(tag.replace("-", " "))

        # remove duplicate tags
        tags_to_include = list(dict.fromkeys(tags_to_include))

        # if visible tags list contains ONLY "also", "often", "sometimes", or "usually" on their own, make them invisible
        if tags_to_include in [["also"], ["often"], ["sometimes"], ["usually"]]:
            tags_to_include = []

        if len(tags_to_include) >= 1:
            definition += "("

            for tag in tags_to_include:
                superstring_found = False

                # don't add tag to definition text if it's a substring of another tag
                for other_tag in tags_to_include:
                    if tag != other_tag and tag in other_tag:
                        superstring_found = True

                if not superstring_found:
                    definition += tag + ", "

            definition = definition[:-2] + ") "

        definition += sense["gloss"] + " ["
        definition += get_pos_abbr(sense["pos"])

        forms = []

        for form in sense["forms"]:
            form_unidecoded = unidecode(form).upper()

            if form_unidecoded.isalpha() and form_unidecoded not in forms:
                forms.append(form_unidecoded)

        if len(forms) >= 1:
            definition += " "

            for form in forms:
                definition += form + ", "

            definition = definition[:-2] + "]"
        else:
            definition += "]"

        sense["def"] = definition

print("Done.")
print("Deleting duplicate definitions...")

digests = {}

for headword in headwords:
    for sense in list(headwords[headword]):
        digest = hashlib.md5((sense["word"] + sense["def"]).encode("UTF-8")).hexdigest()

        if digest in digests.keys():
            headwords[headword].remove(sense)
        else:
            sense["md5"] = digest
            digests[digest] = sense

print("Done.")
print(f"Outputting {len(headwords)} headwords to headwords.txt...")

headwords_out.write(unidecode(json.dumps(headwords, indent=4) + "\n"))

print("Data outputted to headwords.txt.")
print("Auto-assessing some senses...")

auto_assessed = 0

for digest in digests:
    status = ""

    if digests[digest]["pos"] == "name" or "slur" in digests[digest]["tags"]:
        status = "-"

    if status != "":
        statuses_out.write(f"{digest} {status}\n")
        auto_assessed += 1

print(f"Outputted {auto_assessed} auto-assessed senses to statuses.txt.")
print("Closing files...")

headwords_out.close()
statuses_out.close()