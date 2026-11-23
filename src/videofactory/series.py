"""Video series: each has its own topic list (question + Wikipedia article), presenter/category, and writing brief."""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Series:
    key: str
    name: str
    category: str  # decides presenter + colours
    brief: str  # extra instruction for the script writer
    topics: tuple[tuple[str, str], ...]  # (question / display title, Wikipedia article)


SERIES: dict[str, Series] = {s.key: s for s in (
    Series("how", "How does it work?", "technology",
           "This video answers the question '{q}'. The title must be this question (it may add a short hook). "
           "Scene 2 gives the one-sentence answer, then explain the mechanism step by step with process_flow, "
           "cycle or network visuals, using an everyday example from the source.",
           (("How does GPS work?", "Global Positioning System"), ("How does UPI work?", "Unified Payments Interface"),
            ("How does a refrigerator work?", "Refrigerator"), ("How do vaccines work?", "Vaccine"),
            ("How does Wi-Fi work?", "Wi-Fi"), ("How does a microwave oven work?", "Microwave oven"),
            ("How do airplanes fly?", "Lift (force)"), ("How does the internet work?", "Internet"),
            ("How do solar panels work?", "Solar panel"), ("How does a touchscreen work?", "Touchscreen"),
            ("How does an electric car work?", "Electric car"), ("How does a nuclear power plant work?", "Nuclear power plant"),
            ("How does the heart pump blood?", "Heart"), ("How does a camera work?", "Camera"),
            ("How does a QR code work?", "QR code"), ("How does a lithium-ion battery work?", "Lithium-ion battery"),
            ("How do elevators work?", "Elevator"), ("How does an MRI scan work?", "Magnetic resonance imaging"))),
    Series("why", "Why does it happen?", "science",
           "This video answers the curious question '{q}'. The title must be this question (it may add a short hook). "
           "Scene 2 gives the short answer, then explain WHY step by step, using process_flow, cycle, function_graph "
           "or comparison visuals. Keep it fun and surprising, but only use facts from the source.",
           (("Why is the sky blue?", "Rayleigh scattering"), ("Why do we dream?", "Dream"),
            ("Why is the sea salty?", "Seawater"), ("Why does ice float?", "Ice"), ("Why do we get hiccups?", "Hiccup"),
            ("Why do leaves change colour?", "Autumn leaf color"), ("Why do we yawn?", "Yawn"),
            ("Why does the Moon change shape?", "Lunar phase"), ("Why do we have seasons?", "Season"),
            ("Why do cats purr?", "Purr"), ("Why do we sleep?", "Sleep"), ("Why does thunder happen?", "Thunder"),
            ("Why do we get goosebumps?", "Goose bumps"), ("Why do stars twinkle?", "Twinkling"),
            ("Why do we sneeze?", "Sneeze"), ("Why does the sea have tides?", "Tide"), ("Why do we feel pain?", "Pain"),
            ("Why is blood red?", "Hemoglobin"))),
    Series("history", "History in 5 minutes", "history",
           "Tell the history of '{q}' as a clear story in chronological order: use a timeline, big_number and "
           "concept_map visuals. Title format: '{q} explained in 5 minutes' or a similar accurate hook.",
           (("Indus Valley Civilisation", "Indus Valley Civilisation"), ("Maurya Empire", "Maurya Empire"),
            ("Mughal Empire", "Mughal Empire"), ("The printing press", "Printing press"), ("Apollo 11", "Apollo 11"),
            ("Gupta Empire", "Gupta Empire"), ("Chola dynasty", "Chola dynasty"), ("Roman Empire", "Roman Empire"),
            ("Ancient Egypt", "Ancient Egypt"), ("French Revolution", "French Revolution"),
            ("Industrial Revolution", "Industrial Revolution"), ("The Silk Road", "Silk Road"),
            ("Vijayanagara Empire", "Vijayanagara Empire"), ("Indian independence movement", "Indian independence movement"),
            ("The Renaissance", "Renaissance"), ("The invention of the wheel", "Wheel"))),
    Series("money", "Money basics", "finance",
           "Explain '{q}' for beginners with everyday examples, graphs (function_graph, line_chart, pie_chart) and "
           "formulas from the source. This is general education, NOT personal financial advice: never tell viewers "
           "what to buy or promise returns.",
           (("Compound interest", "Compound interest"), ("Inflation", "Inflation"), ("Stock market", "Stock market"),
            ("Credit score", "Credit score"), ("GST in India", "Goods and Services Tax (India)"), ("Mutual funds", "Mutual fund"),
            ("Index funds", "Index fund"), ("Fixed deposits", "Time deposit"), ("Recession", "Recession"),
            ("Interest rates", "Interest rate"), ("Insurance", "Insurance"), ("Cryptocurrency", "Cryptocurrency"),
            ("Rupee cost averaging", "Dollar cost averaging"), ("Diversification", "Diversification (finance)"),
            ("Bonds", "Bond (finance)"), ("Supply and demand", "Supply and demand"))),
    Series("space", "Space & science", "mathematics",
           "Explain '{q}' with a sense of wonder: big_number for huge scales, timeline for missions, concept_map, cycle "
           "and process_flow for how things form. Only numbers from the source.",
           (("Black holes", "Black hole"), ("How stars are born", "Star formation"), ("Chandrayaan-3", "Chandrayaan-3"),
            ("The Solar System", "Solar System"), ("The speed of light", "Speed of light"), ("Mars", "Mars"),
            ("The Moon", "Moon"), ("The Sun", "Sun"), ("The Milky Way", "Milky Way"), ("The Big Bang", "Big Bang"),
            ("Exoplanets", "Exoplanet"), ("The International Space Station", "International Space Station"),
            ("Aditya-L1", "Aditya-L1"), ("Neutron stars", "Neutron star"), ("Comets", "Comet"), ("Galaxies", "Galaxy"))),
    Series("mind", "Psychology & mind", "psychology",
           "Explain '{q}' and how it shows up in everyday life, using pyramid, venn, cycle, comparison and concept_map "
           "visuals. Include practical takeaways only if the source supports them; no medical advice.",
           (("Procrastination", "Procrastination"), ("Confirmation bias", "Confirmation bias"),
            ("The Dunning–Kruger effect", "Dunning–Kruger effect"), ("Habits", "Habit"), ("Memory", "Memory"),
            ("The placebo effect", "Placebo"), ("Cognitive dissonance", "Cognitive dissonance"), ("Motivation", "Motivation"),
            ("Growth mindset", "Growth mindset"), ("Flow state", "Flow (psychology)"), ("Impostor syndrome", "Impostor syndrome"),
            ("The anchoring effect", "Anchoring effect"), ("Maslow's hierarchy of needs", "Maslow's hierarchy of needs"),
            ("Emotional intelligence", "Emotional intelligence"))),
    Series("tech", "Tech explained", "ai",
           "Explain '{q}' simply with analogies from the source, using network, process_flow, comparison and timeline "
           "visuals. Avoid hype; stick to what the source says.",
           (("Artificial intelligence", "Artificial intelligence"), ("ChatGPT", "ChatGPT"), ("Blockchain", "Blockchain"),
            ("5G", "5G"), ("The CPU", "Central processing unit"), ("Cloud computing", "Cloud computing"),
            ("Machine learning", "Machine learning"), ("Large language models", "Large language model"),
            ("Quantum computing", "Quantum computing"), ("Encryption", "Encryption"), ("Semiconductors", "Semiconductor"),
            ("Operating systems", "Operating system"), ("Computer viruses", "Computer virus"),
            ("Search engines", "Search engine"), ("Augmented reality", "Augmented reality"))),
    Series("india", "India GK", "history",
           "Explain '{q}' as an interesting general-knowledge video about India: key facts, timeline and big_number "
           "visuals. Neutral and factual; no political opinions.",
           (("ISRO", "Indian Space Research Organisation"), ("The Constitution of India", "Constitution of India"),
            ("The Green Revolution in India", "Green Revolution in India"), ("Indian Railways", "Indian Railways"),
            ("Diwali", "Diwali"), ("Holi", "Holi"), ("The Taj Mahal", "Taj Mahal"), ("The Ganges", "Ganges"),
            ("The Himalayas", "Himalayas"), ("The Reserve Bank of India", "Reserve Bank of India"),
            ("The Election Commission of India", "Election Commission of India"), ("Kumbh Mela", "Kumbh Mela"),
            ("Aadhaar", "Aadhaar"), ("The Red Fort", "Red Fort"), ("The Golden Temple", "Golden Temple"),
            ("Pongal", "Pongal (festival)"))),
)}


def pick(series_key: str | None, rng: random.Random) -> tuple[Series, str, str]:
    """Returns (series, question/display title, Wikipedia article)."""
    if series_key in (None, "random"):
        series_key = rng.choice(list(SERIES))
    if series_key not in SERIES:
        raise ValueError(f"Unknown series {series_key!r}. Choose from: {', '.join(SERIES)}")
    s = SERIES[series_key]
    q, article = rng.choice(s.topics)
    return s, q, article
