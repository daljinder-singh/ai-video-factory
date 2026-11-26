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
    books: tuple[str, ...] = ()  # OpenStax textbooks to search for a matching section
    nasa: bool = False  # also search science.nasa.gov


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
            ("How do elevators work?", "Elevator"), ("How does an MRI scan work?", "Magnetic resonance imaging")),
           books=("College Physics 2e", "Introduction to Computer Science")),
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
            ("Why is blood red?", "Hemoglobin")),
           books=("Biology 2e", "College Physics 2e", "Chemistry 2e", "Psychology 2e")),
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
            ("Bonds", "Bond (finance)"), ("Supply and demand", "Supply and demand")),
           books=("Principles of Finance 2e", "Principles of Economics 3e")),
    Series("space", "Space & science", "mathematics",
           "Explain '{q}' with a sense of wonder: big_number for huge scales, timeline for missions, concept_map, cycle "
           "and process_flow for how things form. Only numbers from the source.",
           (("Black holes", "Black hole"), ("How stars are born", "Star formation"), ("Chandrayaan-3", "Chandrayaan-3"),
            ("The Solar System", "Solar System"), ("The speed of light", "Speed of light"), ("Mars", "Mars"),
            ("The Moon", "Moon"), ("The Sun", "Sun"), ("The Milky Way", "Milky Way"), ("The Big Bang", "Big Bang"),
            ("Exoplanets", "Exoplanet"), ("The International Space Station", "International Space Station"),
            ("Aditya-L1", "Aditya-L1"), ("Neutron stars", "Neutron star"), ("Comets", "Comet"), ("Galaxies", "Galaxy")),
           books=("Astronomy 2e",), nasa=True),
    Series("mind", "Psychology & mind", "psychology",
           "Explain '{q}' and how it shows up in everyday life, using pyramid, venn, cycle, comparison and concept_map "
           "visuals. Include practical takeaways only if the source supports them; no medical advice.",
           (("Procrastination", "Procrastination"), ("Confirmation bias", "Confirmation bias"),
            ("The Dunning–Kruger effect", "Dunning–Kruger effect"), ("Habits", "Habit"), ("Memory", "Memory"),
            ("The placebo effect", "Placebo"), ("Cognitive dissonance", "Cognitive dissonance"), ("Motivation", "Motivation"),
            ("Growth mindset", "Growth mindset"), ("Flow state", "Flow (psychology)"), ("Impostor syndrome", "Impostor syndrome"),
            ("The anchoring effect", "Anchoring effect"), ("Maslow's hierarchy of needs", "Maslow's hierarchy of needs"),
            ("Emotional intelligence", "Emotional intelligence")),
           books=("Psychology 2e",)),
    Series("tech", "Tech explained", "ai",
           "Explain '{q}' simply with analogies from the source, using network, process_flow, comparison and timeline "
           "visuals. Avoid hype; stick to what the source says.",
           (("Artificial intelligence", "Artificial intelligence"), ("ChatGPT", "ChatGPT"), ("Blockchain", "Blockchain"),
            ("5G", "5G"), ("The CPU", "Central processing unit"), ("Cloud computing", "Cloud computing"),
            ("Machine learning", "Machine learning"), ("Large language models", "Large language model"),
            ("Quantum computing", "Quantum computing"), ("Encryption", "Encryption"), ("Semiconductors", "Semiconductor"),
            ("Operating systems", "Operating system"), ("Computer viruses", "Computer virus"),
            ("Search engines", "Search engine"), ("Augmented reality", "Augmented reality")),
           books=("Introduction to Computer Science",)),
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
    Series("ai", "AI explained", "ai",
           "Explain '{q}' clearly and without hype: what it is, how it works step by step (network, process_flow), "
           "real uses and limits, all from the sources.",
           (("Artificial intelligence", "Artificial intelligence"), ("Machine learning", "Machine learning"),
            ("Neural networks", "Neural network (machine learning)"), ("Deep learning", "Deep learning"),
            ("Large language models", "Large language model"), ("Generative AI", "Generative artificial intelligence"),
            ("Computer vision", "Computer vision"), ("Natural language processing", "Natural language processing"),
            ("Reinforcement learning", "Reinforcement learning"), ("Transformers in AI", "Transformer (deep learning architecture)"),
            ("The Turing test", "Turing test"), ("AlphaGo", "AlphaGo"), ("Self-driving cars", "Self-driving car"),
            ("Recommendation systems", "Recommender system"), ("Speech recognition", "Speech recognition"),
            ("Chatbots", "Chatbot")),
           books=("Principles of Data Science", "Introduction to Computer Science")),
    Series("finance", "Financial world", "finance",
           "Explain '{q}' (the financial system and economy) for beginners using function_graph, line_chart, pie_chart, "
           "process_flow and comparison visuals. General education only: never investment advice or predictions.",
           (("How banks work", "Bank"), ("Central banks", "Central bank"), ("Stock exchanges", "Stock exchange"),
            ("Bombay Stock Exchange", "Bombay Stock Exchange"), ("National Stock Exchange of India", "National Stock Exchange of India"),
            ("What is an IPO?", "Initial public offering"), ("The foreign exchange market", "Foreign exchange market"),
            ("GDP", "Gross domestic product"), ("Fiscal policy", "Fiscal policy"), ("Monetary policy", "Monetary policy"),
            ("Venture capital", "Venture capital"), ("The 2008 financial crisis", "2007–2008 financial crisis"),
            ("The Great Depression", "Great Depression"), ("The Sensex", "BSE SENSEX"), ("Nifty 50", "NIFTY 50"),
            ("Credit cards", "Credit card")),
           books=("Principles of Finance 2e", "Principles of Economics 3e", "Introduction to Business 2e")),
    Series("infrastructure", "Mega structures", "technology",
           "Tell the story of '{q}': why it was built, how it was engineered (process_flow), record numbers "
           "(big_number, bar_chart) and a timeline. Exact numbers from the sources only.",
           (("Burj Khalifa", "Burj Khalifa"), ("Chenab Rail Bridge", "Chenab Rail Bridge"),
            ("Golden Gate Bridge", "Golden Gate Bridge"), ("Panama Canal", "Panama Canal"), ("Suez Canal", "Suez Canal"),
            ("Three Gorges Dam", "Three Gorges Dam"), ("Bhakra Dam", "Bhakra Dam"), ("Delhi Metro", "Delhi Metro"),
            ("Atal Setu (Mumbai Trans Harbour Link)", "Mumbai Trans Harbour Link"), ("Bandra–Worli Sea Link", "Bandra–Worli Sea Link"),
            ("Channel Tunnel", "Channel Tunnel"), ("Great Wall of China", "Great Wall of China"),
            ("Statue of Unity", "Statue of Unity"), ("Atal Tunnel", "Atal Tunnel"), ("Hoover Dam", "Hoover Dam"),
            ("Howrah Bridge", "Howrah Bridge"))),
    Series("geography", "Our planet", "history",
           "Explain the geography of '{q}': where it is, how it formed (process_flow or cycle), key numbers "
           "(big_number), climate and life. Exact numbers from the sources only.",
           (("The Sahara Desert", "Sahara"), ("The Amazon rainforest", "Amazon rainforest"), ("Mount Everest", "Mount Everest"),
            ("The Nile", "Nile"), ("The Pacific Ocean", "Pacific Ocean"), ("Antarctica", "Antarctica"),
            ("The Great Barrier Reef", "Great Barrier Reef"), ("The Thar Desert", "Thar Desert"),
            ("The Western Ghats", "Western Ghats"), ("The Deccan Plateau", "Deccan Plateau"), ("Volcanoes", "Volcano"),
            ("Earthquakes", "Earthquake"), ("The monsoon", "Monsoon of South Asia"), ("The Mariana Trench", "Mariana Trench"),
            ("The Grand Canyon", "Grand Canyon"), ("The Sundarbans", "Sundarbans")),
           ),
    Series("biography", "Great lives", "mathematics",
           "Tell the life story of '{q}' in chronological order (timeline), key achievements (concept_map) and "
           "lasting impact. Strictly factual and respectful: no invented quotes, dates only from the sources.",
           (("A. P. J. Abdul Kalam", "A. P. J. Abdul Kalam"), ("Marie Curie", "Marie Curie"),
            ("Albert Einstein", "Albert Einstein"), ("C. V. Raman", "C. V. Raman"), ("Srinivasa Ramanujan", "Srinivasa Ramanujan"),
            ("Homi J. Bhabha", "Homi J. Bhabha"), ("Vikram Sarabhai", "Vikram Sarabhai"), ("Kalpana Chawla", "Kalpana Chawla"),
            ("Nikola Tesla", "Nikola Tesla"), ("Ada Lovelace", "Ada Lovelace"), ("Isaac Newton", "Isaac Newton"),
            ("Galileo Galilei", "Galileo Galilei"), ("Aryabhata", "Aryabhata"), ("Rabindranath Tagore", "Rabindranath Tagore"),
            ("Jagadish Chandra Bose", "Jagadish Chandra Bose"), ("Charles Darwin", "Charles Darwin"),
            ("Leonardo da Vinci", "Leonardo da Vinci"), ("Ratan Tata", "Ratan Tata"))),
    Series("biology", "Biology made simple", "science",
           "Explain '{q}' with process_flow, cycle, concept_map and comparison visuals, using the textbook and "
           "encyclopedia sources.",
           (("Cells", "Cell (biology)"), ("DNA", "DNA"), ("Photosynthesis", "Photosynthesis"), ("The immune system", "Immune system"),
            ("Evolution", "Evolution"), ("The human brain", "Human brain"), ("The digestive system", "Human digestive system"),
            ("Viruses", "Virus"), ("Bacteria", "Bacteria"), ("Mitochondria", "Mitochondrion"), ("Enzymes", "Enzyme"),
            ("Blood", "Blood"), ("Genes", "Gene"), ("Proteins", "Protein"), ("Cell division (mitosis)", "Mitosis"),
            ("Neurons", "Neuron"), ("The human microbiome", "Human microbiome")),
           books=("Biology 2e", "Concepts of Biology", "Anatomy and Physiology 2e", "Microbiology")),
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
