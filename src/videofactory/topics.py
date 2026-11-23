"""Random topic selection from a curated catalog of Wikipedia articles (every topic has a reliable source)."""
from __future__ import annotations

import random
from dataclasses import dataclass

CATALOG: dict[str, list[str]] = {
    "mathematics": [
        "Pythagorean theorem", "Prime number", "Fibonacci sequence", "Golden ratio", "Pi",
        "Probability", "Logarithm", "Binary number", "Derivative", "Monty Hall problem",
        "Normal distribution", "Euler's identity",
    ],
    "science": [
        "Photosynthesis", "Water cycle", "Black hole", "DNA", "Plate tectonics",
        "Greenhouse effect", "Vaccine", "Speed of light", "Carbon cycle", "Nuclear fusion",
        "Mitochondrion", "Gravity",
    ],
    "programming": [
        "Recursion (computer science)", "Binary search algorithm", "Hash table", "Sorting algorithm",
        "Big O notation", "Object-oriented programming", "Linked list", "Stack (abstract data type)",
        "Version control", "Compiler",
    ],
    "finance": [
        "Compound interest", "Inflation", "Stock market", "Diversification (finance)", "Credit score",
        "Bond (finance)", "Mutual fund", "Interest rate", "Cryptocurrency", "Index fund",
    ],
    "ai": [
        "Neural network (machine learning)", "Machine learning", "Large language model",
        "Reinforcement learning", "Computer vision", "Natural language processing",
        "Gradient descent", "Decision tree", "Transformer (deep learning architecture)",
    ],
    "business": [
        "Supply and demand", "Opportunity cost", "Economies of scale", "Brand", "SWOT analysis",
        "Franchising", "Startup company", "Marketing mix", "Return on investment",
    ],
    "history": [
        "Printing press", "Industrial Revolution", "Silk Road", "Roman Empire", "Apollo 11",
        "Indus Valley Civilisation", "Renaissance", "Invention of the telephone", "Maurya Empire",
        "Green Revolution",
    ],
    "psychology": [
        "Cognitive bias", "Confirmation bias", "Maslow's hierarchy of needs", "Classical conditioning",
        "Dunning–Kruger effect", "Placebo", "Procrastination", "Memory", "Flow (psychology)",
        "Growth mindset",
    ],
    "technology": [
        "Internet", "GPS", "Blockchain", "Transistor", "Cloud computing", "Wi-Fi",
        "Solar cell", "Lithium-ion battery", "5G", "Encryption",
    ],
}


@dataclass(frozen=True)
class Topic:
    category: str
    title: str  # Wikipedia article title


def pick_topic(category: str | None = None, rng: random.Random | None = None) -> Topic:
    rng = rng or random.Random()
    if category is not None and category not in CATALOG:
        raise ValueError(f"Unknown category {category!r}. Choose from: {', '.join(CATALOG)}")
    cat = category or rng.choice(list(CATALOG))
    return Topic(cat, rng.choice(CATALOG[cat]))


def category_of(title: str) -> str:
    for cat, titles in CATALOG.items():
        if title in titles:
            return cat
    return "science"
