"""Pick Twemoji pictures for ingredients, cooking actions and dishes (keyword rules, deterministic)."""
from __future__ import annotations

import re

INGREDIENTS = [
    (("flour", "atta", "maida", "wheat", "semolina", "suji", "rava", "besan"), "1f33e"),
    (("rice", "basmati", "poha"), "1f35a"),
    (("dal", "lentil", "gram", "urad", "moong", "chana", "chickpea", "bean", "rajma", "kidney"), "1fad8"),
    (("onion", "shallot"), "1f9c5"), (("garlic",), "1f9c4"), (("ginger",), "1fada"), (("tomato",), "1f345"),
    (("potato", "aloo"), "1f954"), (("carrot", "gajar"), "1f955"),
    (("capsicum", "bell pepper"), "1fad1"), (("chili", "chile", "chilli", "chillies", "chilies"), "1f336"),
    (("egg",), "1f95a"), (("milk", "cream", "malai"), "1f95b"), (("yogurt", "yoghurt", "curd", "dahi", "buttermilk"), "1f963"),
    (("butter", "ghee"), "1f9c8"), (("oil",), "1fad2"), (("salt",), "1f9c2"),
    (("jaggery", "honey", "gur"), "1f36f"), (("sugar",), "1f36c"), (("water", "ice"), "1f4a7"),
    (("lemon", "lime"), "1f34b"), (("coconut",), "1f965"), (("chicken",), "1f357"),
    (("mutton", "lamb", "meat", "beef", "pork", "goat"), "1f356"), (("fish",), "1f41f"), (("prawn", "shrimp"), "1f990"),
    (("paneer", "cheese", "khoa", "khoya"), "1f9c0"), (("bread", "bun", "pav"), "1f35e"), (("pea",), "1fadb"),
    (("corn",), "1f33d"), (("spinach", "coriander", "cilantro", "mint", "curry leaves", "methi", "leaves", "herb", "dill"), "1f96c"),
    (("cucumber",), "1f952"), (("eggplant", "brinjal", "baingan", "aubergine"), "1f346"), (("mango",), "1f96d"),
    (("banana",), "1f34c"), (("almond", "cashew", "pistachio", "peanut", "nut", "walnut"), "1f95c"),
    (("raisin", "sultana"), "1f347"), (("mushroom",), "1f344"), (("tea",), "1f375"), (("coffee",), "2615"),
    (("cardamom", "cumin", "turmeric", "masala", "clove", "cinnamon", "spice", "seed", "powder", "mustard",
      "asafoetida", "hing", "saffron", "pepper", "fenugreek", "nutmeg", "bay"), "1fad9"),
]
ACTIONS = [  # first match wins: waiting/resting beats the ingredient words in the same step
    (("rest", "wait", "cool", "refrigerat", "chill", "overnight", "set aside", "freeze"), "23f2"),
    (("roll", "shape", "flatten", "divide"), "1fad3"),
    (("knead", "dough", "mix", "stir", "whisk", "combine", "beat"), "1f963"),
    (("chop", "cut", "slice", "dice", "mince", "grate", "peel"), "1f52a"),
    (("fry", "saute", "sauté", "brown", "roast", "toast", "flip", "temper", "tadka", "pan"), "1f373"),
    (("boil", "simmer", "cook", "pressure", "steam", "pot"), "1f372"),
    (("bake", "oven", "grill", "flame", "heat"), "1f525"),
    (("soak", "wash", "rinse", "drain"), "1f4a7"),
    (("blend", "grind", "puree", "purée", "paste"), "1f964"),
    (("serve", "garnish", "plate", "enjoy"), "1f37d"),
    (("sprinkle", "season", "salt"), "1f9c2"),
]
DISHES = [
    (("biryani", "pulao", "khichdi", "khichuri", "fried rice", "lemon rice", "egg rice"), "1f35b"),
    (("chapati", "roti", "naan", "paratha", "puri", "bhatoora", "dosa", "bread", "kulcha", "baati"), "1fad3"),
    (("kulfi", "ice cream"), "1f366"),
    (("kheer", "halwa", "barfi", "pedha", "jamun", "jalebi", "pudding", "laddu", "sweet", "ghevar", "meetha", "custard"), "1f36e"),
    (("tea", "chai", "coffee"), "2615"),
    (("lassi", "panna", "jeera", "lemonade", "drink", "buttermilk", "borhani"), "1f964"),
    (("chutney", "pickle", "sauce", "raita", "kuddi", "churri"), "1f963"),
    (("pakoda", "bhajji", "fritter", "samosa", "bonda", "vada", "punugu", "bada", "balls"), "1f9c6"),
    (("omelet", "egg"), "1f373"), (("chicken",), "1f357"), (("prawn", "fish"), "1f990"), (("soup", "stew"), "1f372"),
    (("curry", "dal", "masala", "chole", "cholley", "gravy", "bartha", "makhani", "korma", "vindaloo", "tikka"), "1f35b"),
]


def _match(text: str, table, default: str | None) -> str | None:
    low = text.lower()
    for keys, code in table:
        for k in keys:
            if re.search(rf"\b{re.escape(k)}", low):
                return code
    return default


def ingredient_icon(name: str) -> str:
    return _match(name, INGREDIENTS, "1f963")


def action_icon(step: str) -> str:
    return _match(step, ACTIONS, "1f373")


def dish_icon(title: str) -> str:
    return _match(title, DISHES, "1f37d")


def all_codes() -> set[str]:
    return {c for _, c in INGREDIENTS + ACTIONS + DISHES} | {"1f963", "1f373", "1f37d", "2728"}
