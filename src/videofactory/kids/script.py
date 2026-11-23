"""Build a kids video script (list of scenes) from curated lessons. Deterministic: no AI, no facts to get wrong.

A scene = {"type", "parts", "data"}. "parts" is the narration as a list of sentences (str) and pauses (float seconds);
visual elements are tied to part indexes, so they appear exactly when their sentence starts."""
from __future__ import annotations

import random

from .lessons import _N_EN, _N_HI, COUNTABLES, TOPICS, Item, Topic

HI_LETTER = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                     ["ए", "बी", "सी", "डी", "ई", "एफ़", "जी", "एच", "आई", "जे", "के", "एल", "एम", "एन", "ओ", "पी",
                      "क्यू", "आर", "एस", "टी", "यू", "वी", "डब्ल्यू", "एक्स", "वाई", "ज़ेड"]))
COUNT_HI = {"1f986": ("बत्तख", "बत्तखें"), "1f34e": ("सेब", "सेब"), "2b50": ("तारा", "तारे"),
            "1f388": ("गुब्बारा", "गुब्बारे"), "1f41f": ("मछली", "मछलियाँ"), "1f697": ("कार", "कारें"),
            "1f338": ("फूल", "फूल"), "1f98b": ("तितली", "तितलियाँ"), "1f36a": ("बिस्कुट", "बिस्कुट"),
            "1f424": ("चूज़ा", "चूज़े")}
PLURAL_EN = {"grapes"}
# what the English voice should SAY for each letter; screen/subtitles show the letter itself
SAY_EN = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                  ["Ay", "Bee", "See", "Dee", "Ee", "Ef", "Jee", "Aitch", "Eye", "Jay", "Kay", "El", "Em", "En", "Oh",
                   "Pee", "Cue", "Ar", "Es", "Tee", "You", "Vee", "Double you", "Ex", "Why", "Zee"]))


def L_(letter: str) -> str:
    """Markup '[[shown|spoken]]': subtitles show the letter, the voice says its name."""
    return f"[[{letter}|{SAY_EN[letter]}]]"
MIXES = [("red", "yellow", "orange"), ("blue", "yellow", "green"), ("red", "blue", "purple")]
SIDES = {"triangle": 3, "square": 4, "rectangle": 4}
WHERE = [("car", "road"), ("airplane", "sky"), ("boat", "water"), ("bus", "road"), ("helicopter", "sky"),
         ("ship", "water")]
FRUIT_GROUPS = {"red": ["apple", "strawberry", "cherry"], "yellow": ["banana", "lemon", "pineapple"]}
GROUP_HI = {"red": "लाल", "yellow": "पीले"}  # plural agreement: "ये फल पीले हैं"
LEARN_HI = {"colours": "रंग", "shapes": "आकार", "numbers": "गिनती", "abc": "ABC",
            "animals": "जानवरों की आवाज़ें", "fruits": "फलों के नाम", "vehicles": "गाड़ियों के नाम"}


def a_an(word: str) -> str:
    if word in PLURAL_EN:
        return word
    return ("an " if word[0] in "aeiou" else "a ") + word


def this_is(word: str) -> str:
    return f"These are {word}." if word in PLURAL_EN else f"This is {a_an(word)}."


class KidsScript:
    def __init__(self, topic: Topic, lang: str, rng: random.Random):
        self.t, self.lang, self.rng = topic, lang, rng
        self.hi = lang == "hi"

    def say(self, en: str | list[str], hi: str | list[str]) -> str:
        choice = hi if self.hi else en
        return self.rng.choice(choice) if isinstance(choice, list) else choice

    def name(self, it: Item) -> str:
        return it.hi if self.hi else it.en

    def item_data(self, it: Item) -> dict:
        return {"en": it.en, "hi": it.hi, "emoji": it.emoji, "color": it.color, "shape": it.shape,
                "letter": it.letter}

    # ------------------------------------------------------------------ scenes
    def intro(self, items: list[Item]) -> dict:
        title = LEARN_HI[self.t.key] if self.hi else self.t.title_en.lower()
        parts = [self.say([f"Hello friends! Today we will learn {title}!", f"Hi everyone! Let's learn {title} together!"],
                          [f"नमस्ते दोस्तों! आज हम {title} सीखेंगे!", f"हैलो बच्चों! चलो साथ में {title} सीखते हैं!"]),
                 self.say(["Are you ready? Let's go!", "It will be so much fun. Let's go!"],
                          ["क्या तुम तैयार हो? चलो शुरू करते हैं!", "बहुत मज़ा आएगा। चलो शुरू करें!"])]
        emojis = [it.emoji for it in items if it.emoji][:6] or [c[0] for c in COUNTABLES[:6]]
        return {"type": "intro", "parts": parts, "data": {"title_en": self.t.title_en, "title_hi": self.t.title_hi,
                                                          "emoji": self.t.emoji, "emojis": emojis}}

    def colour(self, it: Item) -> dict:
        n = self.name(it)
        parts = [self.say(f"This is {n}.", f"यह {n} रंग है।"), f"{n.capitalize()}!" if not self.hi else f"{n}!"]
        exs = list(zip(it.examples, it.examples_en, it.examples_hi))[:3]
        for emo, en, hi in exs:
            parts.append(self.say([f"The {en} is {n}.", f"Look, a {n} {en}!"], [f"{hi} का रंग {n} है।"]))
        parts += [self.say(f"Can you say {n}?", f"क्या तुम {n} बोल सकते हो?"), 1.4]
        return {"type": "colour", "parts": parts, "data": {**self.item_data(it), "examples": [e[0] for e in exs]}}

    def colour_mix(self, a: Item, b: Item, c: Item) -> dict:
        parts = [self.say(["Let's mix colours!", "Time for some colour magic!"], ["चलो रंग मिलाते हैं!", "अब रंगों का जादू देखो!"]),
                 self.say(f"{self.name(a).capitalize()} and {self.name(b)}.", f"{self.name(a)} और {self.name(b)}।"),
                 self.say(f"Together they make {self.name(c)}!", f"दोनों मिलकर {self.name(c)} बनता है!"),
                 self.say(f"Wow, {self.name(c)}!", f"वाह, {self.name(c)}!")]
        return {"type": "colour_mix", "parts": parts,
                "data": {"a": self.item_data(a), "b": self.item_data(b), "c": self.item_data(c)}}

    def shape(self, it: Item) -> dict:
        n = self.name(it)
        parts = [self.say(f"This is {a_an(n)}.", f"यह {n} है।"), f"{n.capitalize()}!" if not self.hi else f"{n}!"]
        exs = list(zip(it.examples, it.examples_en, it.examples_hi))[:2]
        for emo, en, hi in exs:
            parts.append(self.say([f"Look, the {en} is shaped like {a_an(n)}!"], [f"देखो, {hi} का आकार {n} है।"]))
        parts += [self.say(f"Can you draw {a_an(n)} in the air?", f"क्या तुम हवा में {n} बना सकते हो?"), 1.4]
        return {"type": "shape", "parts": parts, "data": {**self.item_data(it), "examples": [e[0] for e in exs]}}

    def shape_sides(self, it: Item) -> dict:
        k = SIDES[it.en]
        n = self.name(it)
        parts = [self.say(f"Let's count the sides of {a_an(n)}.", f"चलो {n} की भुजाएँ गिनते हैं।")]
        parts += [(_N_HI[i] if self.hi else _N_EN[i].capitalize()) + ("।" if self.hi else ".") for i in range(k)]
        parts.append(self.say(f"{a_an(n).capitalize()} has {_N_EN[k - 1]} sides!", f"{n} की {_N_HI[k - 1]} भुजाएँ होती हैं!"))
        return {"type": "shape_sides", "parts": parts, "data": {**self.item_data(it), "sides": k}}

    def count(self, n: int, thing: tuple) -> dict:
        emo, sing, plur, _ = thing
        hs, hp = COUNT_HI[emo]
        parts = [self.say([f"Number {_N_EN[n - 1]}!", f"Here comes number {_N_EN[n - 1]}!"], [f"संख्या {_N_HI[n - 1]}!"])]
        parts += [(_N_HI[i] if self.hi else _N_EN[i].capitalize()) + ("।" if self.hi else ".") for i in range(n)]
        word = (hs if n == 1 else hp) if self.hi else (sing if n == 1 else plur)
        num = _N_HI[n - 1] if self.hi else _N_EN[n - 1].capitalize()
        parts.append(f"{num} {word}!")
        return {"type": "count", "parts": parts, "data": {"n": n, "emoji": emo}}

    def compare(self, a: int, b: int, thing: tuple) -> dict:
        emo, sing, plur, _ = thing
        hp = COUNT_HI[emo][1]
        big, small = max(a, b), min(a, b)
        parts = [self.say(["Which side has more?", "Which group has more?"], ["किस तरफ़ ज़्यादा हैं?"]), 2.0,
                 self.say(f"{_N_EN[big - 1].capitalize()} {plur} is more than {_N_EN[small - 1]}!",
                          f"{_N_HI[big - 1]} {hp}, {_N_HI[small - 1]} से ज़्यादा हैं!")]
        return {"type": "compare", "parts": parts, "data": {"left": a, "right": b, "emoji": emo}}

    def letter(self, it: Item) -> dict:
        L = it.letter
        spoken = HI_LETTER[L] if self.hi else L_(L)
        w = it.hi if self.hi else it.en
        parts = [f"{spoken}!", self.say(f"{spoken} is for {w}.", f"{spoken} से {w}।"),
                 self.say(f"{spoken}, {spoken}, {w}!", f"{spoken}, {spoken}, {w}!")]
        return {"type": "letter", "parts": parts, "data": self.item_data(it)}

    def animal(self, it: Item) -> dict:
        n = self.name(it)
        snd = it.sound_hi if self.hi else it.sound_en
        parts = [self.say(this_is(n), f"यह {n} है।"),
                 self.say(f"The {n} says {snd.rstrip('!')}!", f"{n} की आवाज़ है, {snd.rstrip('!')}!"),
                 self.say(f"Can you say {snd.rstrip('!')}?", f"क्या तुम बोल सकते हो, {snd.rstrip('!')}?"), 1.2]
        return {"type": "animal", "parts": parts, "data": {**self.item_data(it), "sound": snd}}

    def fruit(self, it: Item) -> dict:
        n = self.name(it)
        parts = [self.say(this_is(n), f"यह {n} है।"), it.fact_hi if self.hi else it.fact_en,
                 self.say(["Yummy!", "Yum, yum!"], ["वाह, स्वादिष्ट!", "यम, यम!"])]
        return {"type": "fruit", "parts": parts, "data": self.item_data(it)}

    def vehicle(self, it: Item) -> dict:
        n = self.name(it)
        snd = it.sound_hi if self.hi else it.sound_en
        parts = [self.say(this_is(n), f"यह {n} है।"), it.fact_hi if self.hi else it.fact_en,
                 self.say(f"The {n} goes {snd.rstrip('!')}!", f"{n} की आवाज़, {snd.rstrip('!')}!")]
        return {"type": "vehicle", "parts": parts, "data": {**self.item_data(it), "sound": snd}}

    def sort_where(self, items: dict[str, Item]) -> dict:
        picks = [(items[k], zone) for k, zone in WHERE if k in items]
        chosen, zones = [], set()
        for it, zone in picks:
            if zone not in zones:
                chosen.append((it, zone))
                zones.add(zone)
        parts = [self.say(["Where do they go?", "Let's see where they go!"], ["ये कहाँ चलते हैं?", "चलो देखें ये कहाँ जाते हैं!"])]
        parts += [it.fact_hi if self.hi else it.fact_en for it, _ in chosen]
        return {"type": "sort_where", "parts": parts,
                "data": {"items": [{**self.item_data(it), "zone": z} for it, z in chosen]}}

    def fruit_groups(self, items: dict[str, Item]) -> dict:
        colours = TOPICS["colours"].items
        cname = {c.en: c for c in colours}
        parts = [self.say("Let's sort fruits by colour!", "चलो फलों को रंग से अलग करें!")]
        groups = []
        for col, names in FRUIT_GROUPS.items():
            fr = [items[n] for n in names if n in items]
            groups.append({"colour": self.item_data(cname[col]), "items": [self.item_data(f) for f in fr]})
            parts.append(self.say(f"These fruits are {col}.", f"ये फल {GROUP_HI[col]} हैं।"))
        return {"type": "fruit_groups", "parts": parts, "data": {"groups": groups}}

    def quiz(self, answer: Item, options: list[Item], kind: str = "find") -> dict:
        n = self.name(answer)
        if kind == "sound":
            snd = answer.sound_hi if self.hi else answer.sound_en
            q = self.say(f"Who says {snd.rstrip('!')}?", f"कौन बोलता है, {snd.rstrip('!')}?")
            a = self.say(f"Yes! The {n} says {snd.rstrip('!')}!", f"शाबाश! यह {n} की आवाज़ है!")
        elif kind == "letter":
            spoken = HI_LETTER[answer.letter] if self.hi else answer.letter
            q = self.say(f"Can you find the letter {L_(answer.letter)}?", f"{spoken} कहाँ है?")
            a = self.say(f"Yes! This is {L_(answer.letter)}!", f"शाबाश! यह रहा {spoken}!")
        else:
            q = self.say(f"Can you find the {n}?", f"क्या तुम {n} ढूँढ सकते हो?")
            a = self.say([f"Yes! Here is the {n}!", f"Great job! That's the {n}!"], [f"शाबाश! यह रहा {n}!"])
        opts = options[:]
        self.rng.shuffle(opts)
        return {"type": "quiz", "parts": [q, 2.2, a],
                "data": {"options": [self.item_data(o) for o in opts], "answer": opts.index(answer), "kind": kind}}

    def count_quiz(self, n: int, thing: tuple) -> dict:
        emo, sing, plur, _ = thing
        hp = COUNT_HI[emo][1]
        parts = [self.say(f"How many {plur} can you see?", f"यहाँ कितने {hp} हैं?"), 2.4,
                 self.say(f"{_N_EN[n - 1].capitalize()}! {_N_EN[n - 1].capitalize()} {plur}!",
                          f"{_N_HI[n - 1]}! {_N_HI[n - 1]} {hp}!")]
        return {"type": "count_quiz", "parts": parts, "data": {"n": n, "emoji": emo}}

    def outro(self) -> dict:
        parts = [self.say(["Great job!", "You did it! Great job!"], ["बहुत बढ़िया!", "शाबाश! तुमने कर दिखाया!"]),
                 self.say(["You learned so much today.", "You are a super learner!"],
                          ["आज तुमने बहुत कुछ सीखा।", "तुम बहुत होशियार हो!"]),
                 self.say("See you next time. Bye bye!", "फिर मिलेंगे। बाय बाय!")]
        return {"type": "outro", "parts": parts, "data": {"emoji": self.t.emoji}}

    # ------------------------------------------------------------------ whole video
    def build(self) -> dict:
        t, rng = self.t, self.rng
        items = list(t.items)
        by_en = {i.en: i for i in items}
        scenes: list[dict] = []
        subtitle = ""
        if t.key == "colours":
            pick = rng.sample(items, 6)
            scenes = [self.intro(pick)] + [self.colour(i) for i in pick]
            col = {c.en: c for c in items}
            for a, b, c in rng.sample(MIXES, 2):
                scenes.append(self.colour_mix(col[a], col[b], col[c]))
            scenes.append(self.quiz(pick[0], rng.sample(pick[1:], 2) + [pick[0]]))
            scenes.append(self.quiz(pick[3], rng.sample([p for p in pick if p is not pick[3]], 2) + [pick[3]]))
        elif t.key == "shapes":
            pick = rng.sample(items, 6)
            scenes = [self.intro(pick)] + [self.shape(i) for i in pick]
            scenes += [self.shape_sides(by_en["triangle"]), self.shape_sides(by_en["square"])]
            scenes.append(self.quiz(pick[2], rng.sample([p for p in pick if p is not pick[2]], 2) + [pick[2]]))
        elif t.key == "numbers":
            things = rng.sample(COUNTABLES, 10)
            scenes = [self.intro([])] + [self.count(n, things[n - 1]) for n in range(1, 11)]
            a, b = rng.sample(range(2, 7), 2)
            scenes.append(self.compare(a, b, rng.choice(COUNTABLES)))
            scenes.append(self.count_quiz(rng.randint(3, 6), rng.choice(COUNTABLES)))
        elif t.key == "abc":
            start = rng.choice([0, 7, 14, 19])
            pick = items[start:start + 7]
            subtitle = f"{pick[0].letter} to {pick[-1].letter}"
            scenes = [self.intro(pick)] + [self.letter(i) for i in pick]
            ans = rng.choice(pick)
            scenes.append(self.quiz(ans, rng.sample([p for p in pick if p is not ans], 2) + [ans], kind="letter"))
        elif t.key == "animals":
            pick = rng.sample(items, 7)
            scenes = [self.intro(pick)] + [self.animal(i) for i in pick]
            for ans in rng.sample(pick, 2):
                scenes.append(self.quiz(ans, rng.sample([p for p in pick if p is not ans], 2) + [ans], kind="sound"))
        elif t.key == "fruits":
            must = [by_en[n] for n in ("apple", "banana")]
            pick = must + rng.sample([i for i in items if i not in must], 5)
            rng.shuffle(pick)
            scenes = [self.intro(pick)] + [self.fruit(i) for i in pick]
            scenes.append(self.fruit_groups(by_en))
            ans = rng.choice(pick)
            scenes.append(self.quiz(ans, rng.sample([p for p in pick if p is not ans], 2) + [ans]))
        elif t.key == "vehicles":
            must = [by_en[n] for n in ("car", "airplane", "boat")]
            pick = must + rng.sample([i for i in items if i not in must], 4)
            rng.shuffle(pick)
            scenes = [self.intro(pick)] + [self.vehicle(i) for i in pick]
            scenes.append(self.sort_where(by_en))
            ans = rng.choice(pick)
            scenes.append(self.quiz(ans, rng.sample([p for p in pick if p is not ans], 2) + [ans]))
        scenes.append(self.outro())
        for i, s in enumerate(scenes):
            s["index"] = i
        return {"topic": t.key, "lang": self.lang, "title_en": t.title_en, "title_hi": t.title_hi,
                "subtitle": subtitle, "scenes": scenes}


def build_script(topic_key: str, lang: str, seed: int) -> dict:
    if topic_key not in TOPICS:
        raise ValueError(f"Unknown kids topic {topic_key!r}. Choose from: {', '.join(TOPICS)}")
    return KidsScript(TOPICS[topic_key], lang, random.Random(seed)).build()
