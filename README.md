# About
This is the code I'm using to make and maintain Ian07's Wiktionary Insanity (IWI), an English-language Wiktionary-based word game lexicon. I'll add a link to it here Soon™ when it's ready (spoiler: this will probably take at least a few months), but I'm posting the code here so that anyone in the present can make their own Wiktionary lexica, perhaps for other languages (which will likely require significant code modification), and so that anyone in the future can maintain the English one whenever I stop regularly updating mine for one reason or another.

Releases of the lexicon itself will be found in the [releases tab](https://github.com/Ian-07/wiktlex/releases) on Github, and are currently planned to occur approximately once per year. The names of these will follow the scheme of "IWI###", where the first two digits are the year (e.g. 25 for 2025) and the last digit is the index of the release within that year (0 for the first, 1 for the second, and so on). This scheme was enforced by Quackle; I wanted to include a dot between the year and the revision number for clarity, but unfortunately Quackle does not support this and also does not properly handle the situation where a user tries to enter a lexicon name containing a dot, making the broken lexicon difficult to remove.

This relies on data originally extracted via Tatu Ylonen's [wiktextract](https://github.com/tatuylonen/wiktextract), so special thanks go to him for making this significantly less headache-inducing.

# Instructions
1. Download the latest version of `raw-wiktextract-data.jsonl` from https://kaikki.org/dictionary/rawdata.html.
   * Note that this is a pretty large file: 18.1 GB as of writing. You could also try the smaller (2.4 GB as of writing) English-entry-only output at https://kaikki.org/dictionary/English/, but I recommend using the full file if you're not low on space, since this one includes Translingual terms, some of which have been accepted into IWI.
   * kaikki.org is regularly updated based on periodic dumps of data from Wiktionary. The dump date should be within the last month.
   * If the site is not available, or if the latest wiktextract output is significantly out of date, then see wiktextract's own README for instructions on installing and running wiktextract yourself.
2. Move the file into this directory.
3. Run initialize.py.
   * You'll be prompted as to which file to use as input. If you haven't changed the name of the file, leave this blank.
   * You'll also be asked whether you want to run a couple of bonus searches for words that are potentially missing from Wiktionary. These only take a few seconds to run, but leave this blank if you'd rather skip them.
   * The script as a whole takes a few minutes to finish on my machine.
4. Run editor.py.
   * This is a Flask app, but you can just locally host it if you're working by yourself.
   * Warning: Assessing every single word will be quite tedious. As of writing, there are nearly half a million headwords with over a million senses. However, I tried to design the editor in a way that streamlines the assessment process as much as possible.
   * Use the box at the top of the homepage to view and edit a specific headword, or use the search options below it to assess words in larger batches. The default search parameters, however, will be sufficient to reach every word that hasn't automatically been rejected.
      * For each sense, click on the green box to accept a sense, red to reject it, or yellow to mark it as "unsure". Blue means the sense is still pending.
      * If all the inflections for a given sense are already accounted for by other senses which have already been accepted, the sense will automatically be deemed "redundant" (denoted by the gray box) and the definition will be crossed out. Although the gray box is not clickable, you can still accept the sense anyway (e.g. if it contains necessary context which is missing from other sense definitions) by clicking the green box as normal. Click the blue box to reset it to "redundant".
      * If a headword has no pending senses remaining, it will not be shown in the search result list by default (though searching for it directly still works). Use "include accepted/rejected/unsure" to search for these.
      * Moving from top to bottom is generally recommended. This is because the senses are ordered so that those which contain self-references are moved to the bottom of the list. Besides this, senses containing larger numbers of inflections (e.g. most verbs compared to most nouns) and senses containing fewer capital letters are moved closer to the top.
      * Sometimes the definitions will be highlighted due to having certain properties (e.g. proper noun, initialism, offensive) which may preclude them being eligible for inclusion. These may still be acceptable, but some additional caution is warranted. See the homepage for a list of what each color means.
      * You can also use the keyboard to speed up the process even further. Use the left and right arrow keys to move around between headwords, and use the indicated number keys to quickly accept the definition with that number.
      * Click the "Save Changes" button at the very bottom of the page once you're done with the batch. This will refresh the page, thus giving you a new batch, assuming you've assessed all the words in the previous batch.
   * The stats page shows statistics for words of each length, as well as the overall progress.
   * Remain on this step until the stats page says there are 0 words still pending. You will probably also want to revisit the "unsure" words prior to finalization by checking the "include unsure" checkbox on the homepage.
5. Run finalize.py.
   * You'll be prompted to enter a name for the lexicon. If left blank, the name will just be "wordlist".
   * You'll also be prompted to enter the filename for a different lexicon (most likely a previous version of the same lexicon) to output a comparison between the two. If you do enter a filename, make sure it's for a plain wordlist that only contains a single word per line. However, you can leave this blank to skip this step.
   * The final lexicon output consists of these three files:
      * `(wordlist name).txt`: Plain wordlist, one word per line.
      * `(wordlist name)_defs.txt`: Wordlist with definitions, one word/definition pair per line.
         * Unfortunately, Zyzzyva does not currently have proper handling for input lines beyond 640 characters in length, so I reluctantly decided to limit this to 629 characters.
      * `(wordlist name)_status.txt`: Stores the status of each sense. Make sure to hold on to this file if you plan on updating the lexicon based on new Wiktionary data later; see step 7 for how to do this.
   * If you selected a previous wordlist for comparison, you'll also get these two files:
      * `(wordlist name)_additions.txt`: A list of words in the new lexicon but not the old one, sorted by length.
      * `(wordlist name)_removals.txt`: A list of words in the old lexicon but not the new one, sorted by length.
6. You *should* now be able to import either of the first two files into any program that can read them.
   * I emphasized "should" because all of the programs listed below have, in my experience, been quite finicky with custom wordlists, so I can't make any guarantees that they will work properly.
   * Definitions optional: [NASPA Zyzzyva](http://www.scrabbleplayers.org/w/NASPA_Zyzzyva_Download), [Collins Zyzzyva](https://scrabble.collinsdictionary.com/tools/), [Infiniwords](https://infiniwords.com/)
      * **WARNING**: There is a possibility that importing `wordlist_defs.txt` into Zyzzyva may result in your computer bluescreening. `wordlist.txt` should work fine, though may result in Zyzzyva taking slightly longer to load.
   * No definitions (use `wordlist.txt`): [Quackle](https://people.csail.mit.edu/jasonkb/quackle/)
7. To update the lexicon based on new data:
   * Perform steps 1-3 using a new version of `raw-wiktextract-data.jsonl`.
   * Open `statuses.txt`, which is basically a working version of the final `wordlist_status.txt` in your favorite text editor. Go to the bottom of the file (make sure you're on an empty line), copy-paste everything from the previous `wordlist_status.txt`, and save.
   * Any definitions which have been added or changed will need to be reassessed unless determined to be redundant. Any definitions which have been removed will no longer be included.
