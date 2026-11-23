"""Curated lesson content for 0-5 year olds (English + Hindi). Hand-written simple facts only.

Emoji codes are Twemoji file names (assets/emoji/twemoji/<code>.svg, CC-BY 4.0)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Item:
    en: str
    hi: str
    emoji: str  # main picture
    color: str = "#FF7043"  # accent colour for the scene
    examples: tuple[str, ...] = ()  # extra pictures (emoji codes)
    examples_en: tuple[str, ...] = ()
    examples_hi: tuple[str, ...] = ()
    sound_en: str = ""  # animal / vehicle sound
    sound_hi: str = ""
    fact_en: str = ""  # one very simple true sentence
    fact_hi: str = ""
    letter: str = ""  # ABC topic
    shape: str = ""  # shapes topic: manim primitive to draw


@dataclass(frozen=True)
class Topic:
    key: str
    title_en: str
    title_hi: str
    emoji: str
    items: tuple[Item, ...] = field(default_factory=tuple)


COLOURS = Topic("colours", "Colours", "रंग", "1f308", (
    Item("red", "लाल", "1f34e", "#E53935", ("1f34e", "1f353", "1f697"), ("apple", "strawberry", "car"),
         ("सेब", "स्ट्रॉबेरी", "कार")),
    Item("blue", "नीला", "1f499", "#1E88E5", ("1f433", "1f4d8", "1f499"), ("whale", "book", "heart"),
         ("व्हेल", "किताब", "दिल")),
    Item("yellow", "पीला", "1f34c", "#FDD835", ("1f34c", "2600", "1f34b"), ("banana", "sun", "lemon"),
         ("केला", "सूरज", "नींबू")),
    Item("green", "हरा", "1f438", "#43A047", ("1f438", "1f966", "1f34f"), ("frog", "broccoli", "apple"),
         ("मेंढक", "ब्रोकली", "सेब")),
    Item("orange", "नारंगी", "1f34a", "#FB8C00", ("1f34a", "1f955", "1f3c0"), ("orange", "carrot", "ball"),
         ("संतरा", "गाजर", "गेंद")),
    Item("purple", "बैंगनी", "1f347", "#8E24AA", ("1f347", "1f346", "1f49c"), ("grapes", "eggplant", "heart"),
         ("अंगूर", "बैंगन", "दिल")),
    Item("pink", "गुलाबी", "1f437", "#EC407A", ("1f437", "1f9a9", "1f338"), ("pig", "flamingo", "flower"),
         ("सुअर", "फ्लेमिंगो", "फूल")),
    Item("brown", "भूरा", "1f43b", "#8D6E63", ("1f43b", "1f330", "1f36a"), ("bear", "nut", "cookie"),
         ("भालू", "मेवा", "बिस्कुट")),
))

SHAPES = Topic("shapes", "Shapes", "आकार", "1f537", (
    Item("circle", "गोला", "26bd", "#42A5F5", ("26bd", "1f36a", "1f550"), ("ball", "cookie", "clock"),
         ("गेंद", "बिस्कुट", "घड़ी"), shape="circle"),
    Item("square", "वर्ग", "1f4e6", "#66BB6A", ("1f381", "1f4e6", "1f5bc"), ("gift", "box", "picture"),
         ("तोहफ़ा", "डिब्बा", "तस्वीर"), shape="square"),
    Item("triangle", "त्रिभुज", "1f355", "#FFA726", ("1f355", "26fa", "1f9c0"), ("pizza", "tent", "cheese"),
         ("पिज़्ज़ा", "तंबू", "चीज़"), shape="triangle"),
    Item("rectangle", "आयत", "1f6aa", "#AB47BC", ("1f6aa", "1f4f1", "1f4d7"), ("door", "phone", "book"),
         ("दरवाज़ा", "फ़ोन", "किताब"), shape="rectangle"),
    Item("star", "तारा", "2b50", "#FDD835", ("2b50", "1f31f", "1f320"), ("star", "shiny star", "shooting star"),
         ("तारा", "चमकता तारा", "टूटता तारा"), shape="star"),
    Item("heart", "दिल", "2764", "#EC407A", ("2764", "1f496", "1f49d"), ("heart", "sparkly heart", "gift heart"),
         ("दिल", "चमकता दिल", "तोहफ़े वाला दिल"), shape="heart"),
    Item("oval", "अंडाकार", "1f95a", "#26A69A", ("1f95a", "1f3c9", "1f95c"), ("egg", "rugby ball", "peanut"),
         ("अंडा", "रग्बी बॉल", "मूंगफली"), shape="oval"),
))

_N_EN = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
_N_HI = ["एक", "दो", "तीन", "चार", "पाँच", "छह", "सात", "आठ", "नौ", "दस"]
# things to count: (emoji, singular en, plural en, hindi)
COUNTABLES = [("1f986", "duck", "ducks", "बत्तख"), ("1f34e", "apple", "apples", "सेब"),
              ("2b50", "star", "stars", "तारे"), ("1f388", "balloon", "balloons", "गुब्बारे"),
              ("1f41f", "fish", "fish", "मछलियाँ"), ("1f697", "car", "cars", "कारें"),
              ("1f338", "flower", "flowers", "फूल"), ("1f98b", "butterfly", "butterflies", "तितलियाँ"),
              ("1f36a", "cookie", "cookies", "बिस्कुट"), ("1f424", "chick", "chicks", "चूज़े")]
NUMBERS = Topic("numbers", "Numbers 1 to 10", "गिनती 1 से 10", "1f522", tuple(
    Item(_N_EN[i], _N_HI[i], "", "#7E57C2", letter=str(i + 1)) for i in range(10)))

_ABC = [("A", "apple", "एप्पल", "1f34e"), ("B", "ball", "बॉल", "26bd"), ("C", "cat", "कैट", "1f431"),
        ("D", "dog", "डॉग", "1f436"), ("E", "elephant", "एलीफ़ेंट", "1f418"), ("F", "fish", "फ़िश", "1f41f"),
        ("G", "grapes", "ग्रेप्स", "1f347"), ("H", "house", "हाउस", "1f3e0"), ("I", "ice cream", "आइसक्रीम", "1f366"),
        ("J", "jellyfish", "जेलीफ़िश", "1fabc"), ("K", "kite", "काइट", "1fa81"), ("L", "lion", "लायन", "1f981"),
        ("M", "monkey", "मंकी", "1f412"), ("N", "nest", "नेस्ट", "1faba"), ("O", "owl", "आउल", "1f989"),
        ("P", "penguin", "पेंगुइन", "1f427"), ("Q", "queen", "क्वीन", "1f478"), ("R", "rabbit", "रैबिट", "1f430"),
        ("S", "sun", "सन", "2600"), ("T", "tiger", "टाइगर", "1f42f"), ("U", "umbrella", "अम्ब्रेला", "2602"),
        ("V", "violin", "वायलिन", "1f3bb"), ("W", "whale", "व्हेल", "1f433"), ("X", "xmas tree", "एक्समस ट्री", "1f384"),
        ("Y", "yo-yo", "यो-यो", "1fa80"), ("Z", "zebra", "ज़ेबरा", "1f993")]
_ABC_COLORS = ["#E53935", "#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#EC407A", "#00ACC1"]
ABC = Topic("abc", "ABC Letters", "ABC अक्षर", "1f524", tuple(
    Item(w, hi, e, _ABC_COLORS[i % len(_ABC_COLORS)], letter=L) for i, (L, w, hi, e) in enumerate(_ABC)))

ANIMALS = Topic("animals", "Animal Sounds", "जानवरों की आवाज़ें", "1f42e", (
    Item("cow", "गाय", "1f404", "#8D6E63", sound_en="moo, moo", sound_hi="मूँ, मूँ"),
    Item("dog", "कुत्ता", "1f415", "#FFB74D", sound_en="woof, woof", sound_hi="भौं, भौं"),
    Item("cat", "बिल्ली", "1f408", "#FF8A65", sound_en="meow, meow", sound_hi="म्याऊँ, म्याऊँ"),
    Item("duck", "बत्तख", "1f986", "#FFD54F", sound_en="quack, quack", sound_hi="क्वैक, क्वैक"),
    Item("sheep", "भेड़", "1f411", "#90A4AE", sound_en="baa, baa", sound_hi="मैं, मैं"),
    Item("lion", "शेर", "1f981", "#FFA726", sound_en="roar!", sound_hi="दहाड़!"),
    Item("rooster", "मुर्गा", "1f413", "#E53935", sound_en="cock a doodle doo", sound_hi="कुकड़ूँ कूँ"),
    Item("frog", "मेंढक", "1f438", "#66BB6A", sound_en="ribbit, ribbit", sound_hi="टर्र, टर्र"),
    Item("bee", "मधुमक्खी", "1f41d", "#FDD835", sound_en="buzz, buzz", sound_hi="भिन, भिन"),
    Item("owl", "उल्लू", "1f989", "#8D6E63", sound_en="hoot, hoot", sound_hi="हू, हू"),
    Item("goat", "बकरी", "1f410", "#A1887F", sound_en="maa, maa", sound_hi="मैं, मैं"),
    Item("horse", "घोड़ा", "1f40e", "#795548", sound_en="neigh!", sound_hi="हिन हिन!"),
))

FRUITS = Topic("fruits", "Fruits", "फल", "1f353", (
    Item("apple", "सेब", "1f34e", "#E53935", fact_en="The apple is red.", fact_hi="सेब लाल होता है।"),
    Item("banana", "केला", "1f34c", "#FDD835", fact_en="The banana is yellow.", fact_hi="केला पीला होता है।"),
    Item("mango", "आम", "1f96d", "#FFA726", fact_en="The mango is sweet.", fact_hi="आम मीठा होता है।"),
    Item("grapes", "अंगूर", "1f347", "#8E24AA", fact_en="Grapes are small and round.", fact_hi="अंगूर छोटे और गोल होते हैं।"),
    Item("orange", "संतरा", "1f34a", "#FB8C00", fact_en="The orange is orange.", fact_hi="संतरा नारंगी होता है।"),
    Item("strawberry", "स्ट्रॉबेरी", "1f353", "#E53935", fact_en="The strawberry is red.", fact_hi="स्ट्रॉबेरी लाल होती है।"),
    Item("watermelon", "तरबूज", "1f349", "#43A047", fact_en="The watermelon is big and green.",
         fact_hi="तरबूज बड़ा और हरा होता है।"),
    Item("pineapple", "अनानास", "1f34d", "#FDD835", fact_en="The pineapple is spiky.", fact_hi="अनानास कांटेदार होता है।"),
    Item("cherry", "चेरी", "1f352", "#C62828", fact_en="Cherries are small and red.", fact_hi="चेरी छोटी और लाल होती है।"),
    Item("pear", "नाशपाती", "1f350", "#9CCC65", fact_en="The pear is green.", fact_hi="नाशपाती हरी होती है।"),
    Item("lemon", "नींबू", "1f34b", "#FDD835", fact_en="The lemon is sour.", fact_hi="नींबू खट्टा होता है।"),
    Item("coconut", "नारियल", "1f965", "#8D6E63", fact_en="The coconut is hard.", fact_hi="नारियल सख़्त होता है।"),
))

VEHICLES = Topic("vehicles", "Vehicles", "गाड़ियाँ", "1f697", (
    Item("car", "कार", "1f697", "#E53935", sound_en="beep, beep", sound_hi="पीं, पीं",
         fact_en="A car goes on the road.", fact_hi="कार सड़क पर चलती है।"),
    Item("bus", "बस", "1f68c", "#FDD835", sound_en="beep, beep", sound_hi="पीं, पीं",
         fact_en="A bus carries many people.", fact_hi="बस में बहुत सारे लोग बैठते हैं।"),
    Item("train", "रेलगाड़ी", "1f682", "#43A047", sound_en="choo, choo", sound_hi="छुक, छुक",
         fact_en="A train goes on the tracks.", fact_hi="रेलगाड़ी पटरी पर चलती है।"),
    Item("airplane", "हवाई जहाज़", "2708", "#1E88E5", sound_en="zoom!", sound_hi="ज़ूम!",
         fact_en="An airplane flies in the sky.", fact_hi="हवाई जहाज़ आसमान में उड़ता है।"),
    Item("ship", "जहाज़", "1f6a2", "#1565C0", sound_en="toot, toot", sound_hi="भोंपू!",
         fact_en="A ship sails on the sea.", fact_hi="जहाज़ समुद्र में चलता है।"),
    Item("bicycle", "साइकिल", "1f6b2", "#26A69A", sound_en="ring, ring", sound_hi="ट्रिन, ट्रिन",
         fact_en="A bicycle has two wheels.", fact_hi="साइकिल के दो पहिए होते हैं।"),
    Item("fire engine", "दमकल", "1f692", "#D32F2F", sound_en="nee naw, nee naw", sound_hi="टन, टन",
         fact_en="A fire engine helps put out fires.", fact_hi="दमकल आग बुझाने में मदद करती है।"),
    Item("tractor", "ट्रैक्टर", "1f69c", "#43A047", sound_en="chug, chug", sound_hi="धक, धक",
         fact_en="A tractor works on the farm.", fact_hi="ट्रैक्टर खेत में काम करता है।"),
    Item("helicopter", "हेलीकॉप्टर", "1f681", "#FB8C00", sound_en="whirr!", sound_hi="घर्र!",
         fact_en="A helicopter flies in the sky.", fact_hi="हेलीकॉप्टर आसमान में उड़ता है।"),
    Item("rocket", "रॉकेट", "1f680", "#7E57C2", sound_en="whoosh!", sound_hi="ज़ूम!",
         fact_en="A rocket goes to space.", fact_hi="रॉकेट अंतरिक्ष में जाता है।"),
    Item("boat", "नाव", "26f5", "#29B6F6", sound_en="splash!", sound_hi="छपाक!",
         fact_en="A boat goes on the water.", fact_hi="नाव पानी पर चलती है।"),
))

TOPICS: dict[str, Topic] = {t.key: t for t in (COLOURS, SHAPES, NUMBERS, ABC, ANIMALS, FRUITS, VEHICLES)}


def all_emoji_codes() -> set[str]:
    codes = {c[0] for c in COUNTABLES}
    for t in TOPICS.values():
        codes.add(t.emoji)
        for it in t.items:
            if it.emoji:
                codes.add(it.emoji)
            codes.update(it.examples)
    return codes
