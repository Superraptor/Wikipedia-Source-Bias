from __future__ import annotations

from typing import Any

# Domain Bias & Reliability Knowledge Base
DOMAIN_BIAS_DATABASE: dict[str, dict[str, Any]] = {
    # News Agencies / Wire Services
    "reuters.com": {
        "name": "Reuters",
        "country": "United Kingdom",
        "region": "Europe",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "English",
        "type": "wire_service",
    },
    "apnews.com": {
        "name": "Associated Press",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "English",
        "type": "wire_service",
    },
    "afp.com": {
        "name": "Agence France-Presse",
        "country": "France",
        "region": "Europe",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "French",
        "type": "wire_service",
    },
    "bloomberg.com": {
        "name": "Bloomberg",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "English",
        "type": "financial_news",
    },
    # Major US Outlets
    "nytimes.com": {
        "name": "The New York Times",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "English",
        "type": "newspaper",
    },
    "washingtonpost.com": {
        "name": "The Washington Post",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "English",
        "type": "newspaper",
    },
    "wsj.com": {
        "name": "The Wall Street Journal",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center-right",
        "reliability": "high",
        "default_language": "English",
        "type": "newspaper",
    },
    "cnn.com": {
        "name": "CNN",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center-left",
        "reliability": "medium",
        "default_language": "English",
        "type": "cable_news",
    },
    "foxnews.com": {
        "name": "Fox News",
        "country": "United States",
        "region": "North America",
        "political_leaning": "right-leaning",
        "reliability": "variable/opinion",
        "default_language": "English",
        "type": "cable_news",
    },
    "msnbc.com": {
        "name": "MSNBC",
        "country": "United States",
        "region": "North America",
        "political_leaning": "left-leaning",
        "reliability": "variable/opinion",
        "default_language": "English",
        "type": "cable_news",
    },
    "npr.org": {
        "name": "National Public Radio",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "English",
        "type": "public_broadcaster",
    },
    "huffpost.com": {
        "name": "HuffPost",
        "country": "United States",
        "region": "North America",
        "political_leaning": "left-leaning",
        "reliability": "medium",
        "default_language": "English",
        "type": "online_news",
    },
    "breitbart.com": {
        "name": "Breitbart News",
        "country": "United States",
        "region": "North America",
        "political_leaning": "far-right",
        "reliability": "variable/opinion",
        "default_language": "English",
        "type": "online_news",
    },
    "latimes.com": {
        "name": "Los Angeles Times",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "English",
        "type": "newspaper",
    },
    "cbsnews.com": {
        "name": "CBS News",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "English",
        "type": "broadcast_news",
    },
    "nbcnews.com": {
        "name": "NBC News",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "English",
        "type": "broadcast_news",
    },
    "abcnews.go.com": {
        "name": "ABC News",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "English",
        "type": "broadcast_news",
    },
    "politico.com": {
        "name": "Politico",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "English",
        "type": "political_news",
    },
    "theatlantic.com": {
        "name": "The Atlantic",
        "country": "United States",
        "region": "North America",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "English",
        "type": "magazine",
    },
    "nationalreview.com": {
        "name": "National Review",
        "country": "United States",
        "region": "North America",
        "political_leaning": "right-leaning",
        "reliability": "medium",
        "default_language": "English",
        "type": "magazine",
    },
    # European Outlets
    "bbc.com": {
        "name": "BBC News",
        "country": "United Kingdom",
        "region": "Europe",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "English",
        "type": "public_broadcaster",
    },
    "bbc.co.uk": {
        "name": "BBC News",
        "country": "United Kingdom",
        "region": "Europe",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "English",
        "type": "public_broadcaster",
    },
    "theguardian.com": {
        "name": "The Guardian",
        "country": "United Kingdom",
        "region": "Europe",
        "political_leaning": "left-leaning",
        "reliability": "high",
        "default_language": "English",
        "type": "newspaper",
    },
    "ft.com": {
        "name": "Financial Times",
        "country": "United Kingdom",
        "region": "Europe",
        "political_leaning": "center-right",
        "reliability": "high",
        "default_language": "English",
        "type": "financial_news",
    },
    "economist.com": {
        "name": "The Economist",
        "country": "United Kingdom",
        "region": "Europe",
        "political_leaning": "center-right",
        "reliability": "high",
        "default_language": "English",
        "type": "magazine",
    },
    "telegraph.co.uk": {
        "name": "The Daily Telegraph",
        "country": "United Kingdom",
        "region": "Europe",
        "political_leaning": "right-leaning",
        "reliability": "high",
        "default_language": "English",
        "type": "newspaper",
    },
    "dailymail.co.uk": {
        "name": "Daily Mail",
        "country": "United Kingdom",
        "region": "Europe",
        "political_leaning": "right-leaning",
        "reliability": "variable/opinion",
        "default_language": "English",
        "type": "tabloid",
    },
    "lemonde.fr": {
        "name": "Le Monde",
        "country": "France",
        "region": "Europe",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "French",
        "type": "newspaper",
    },
    "lefigaro.fr": {
        "name": "Le Figaro",
        "country": "France",
        "region": "Europe",
        "political_leaning": "center-right",
        "reliability": "high",
        "default_language": "French",
        "type": "newspaper",
    },
    "spiegel.de": {
        "name": "Der Spiegel",
        "country": "Germany",
        "region": "Europe",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "German",
        "type": "magazine",
    },
    "zeit.de": {
        "name": "Die Zeit",
        "country": "Germany",
        "region": "Europe",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "German",
        "type": "newspaper",
    },
    "dw.com": {
        "name": "Deutsche Welle",
        "country": "Germany",
        "region": "Europe",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "German",
        "type": "public_broadcaster",
    },
    "elpais.com": {
        "name": "El País",
        "country": "Spain",
        "region": "Europe",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "Spanish",
        "type": "newspaper",
    },
    "corriere.it": {
        "name": "Corriere della Sera",
        "country": "Italy",
        "region": "Europe",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "Italian",
        "type": "newspaper",
    },

    # State-affiliated / International Outlets
    "aljazeera.com": {
        "name": "Al Jazeera English",
        "country": "Qatar",
        "region": "Middle East",
        "political_leaning": "state-affiliated",
        "reliability": "medium",
        "default_language": "English",
        "type": "international_broadcaster",
    },
    "rt.com": {
        "name": "RT (Russia Today)",
        "country": "Russia",
        "region": "Europe",
        "political_leaning": "state-affiliated",
        "reliability": "state-sponsored",
        "default_language": "English",
        "type": "state_media",
    },
    "tass.com": {
        "name": "TASS",
        "country": "Russia",
        "region": "Europe",
        "political_leaning": "state-affiliated",
        "reliability": "state-sponsored",
        "default_language": "Russian",
        "type": "wire_service",
    },
    "chinadaily.com.cn": {
        "name": "China Daily",
        "country": "China",
        "region": "Asia",
        "political_leaning": "state-affiliated",
        "reliability": "state-sponsored",
        "default_language": "English",
        "type": "state_media",
    },
    "xinhuanet.com": {
        "name": "Xinhua News Agency",
        "country": "China",
        "region": "Asia",
        "political_leaning": "state-affiliated",
        "reliability": "state-sponsored",
        "default_language": "Chinese",
        "type": "wire_service",
    },
    "scmp.com": {
        "name": "South China Morning Post",
        "country": "Hong Kong",
        "region": "Asia",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "English",
        "type": "newspaper",
    },

    # Asian / Oceania / Americas Outlets
    "thehindu.com": {
        "name": "The Hindu",
        "country": "India",
        "region": "Asia",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "English",
        "type": "newspaper",
    },
    "timesofindia.indiatimes.com": {
        "name": "Times of India",
        "country": "India",
        "region": "Asia",
        "political_leaning": "center",
        "reliability": "medium",
        "default_language": "English",
        "type": "newspaper",
    },
    "ndtv.com": {
        "name": "NDTV",
        "country": "India",
        "region": "Asia",
        "political_leaning": "center-left",
        "reliability": "medium",
        "default_language": "English",
        "type": "broadcast_news",
    },
    "asahi.com": {
        "name": "The Asahi Shimbun",
        "country": "Japan",
        "region": "Asia",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "Japanese",
        "type": "newspaper",
    },
    "yomiuri.co.jp": {
        "name": "The Yomiuri Shimbun",
        "country": "Japan",
        "region": "Asia",
        "political_leaning": "center-right",
        "reliability": "high",
        "default_language": "Japanese",
        "type": "newspaper",
    },
    "nhk.or.jp": {
        "name": "NHK World",
        "country": "Japan",
        "region": "Asia",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "Japanese",
        "type": "public_broadcaster",
    },
    "abc.net.au": {
        "name": "ABC News Australia",
        "country": "Australia",
        "region": "Oceania",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "English",
        "type": "public_broadcaster",
    },
    "cbc.ca": {
        "name": "CBC News",
        "country": "Canada",
        "region": "North America",
        "political_leaning": "center-left",
        "reliability": "high",
        "default_language": "English",
        "type": "public_broadcaster",
    },
    "theglobeandmail.com": {
        "name": "The Globe and Mail",
        "country": "Canada",
        "region": "North America",
        "political_leaning": "center-right",
        "reliability": "high",
        "default_language": "English",
        "type": "newspaper",
    },
    "globo.com": {
        "name": "O Globo",
        "country": "Brazil",
        "region": "South America",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "Portuguese",
        "type": "media_conglomerate",
    },

    # Academic & Scientific Repositories / Publishers
    "doi.org": {
        "name": "DOI Foundation",
        "country": "Global",
        "region": "Global",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "academic_repository",
    },
    "nature.com": {
        "name": "Nature Publishing Group",
        "country": "United Kingdom",
        "region": "Europe",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "scientific_journal",
    },
    "sciencedirect.com": {
        "name": "ScienceDirect (Elsevier)",
        "country": "Netherlands",
        "region": "Europe",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "academic_publisher",
    },
    "ncbi.nlm.nih.gov": {
        "name": "PubMed / NCBI",
        "country": "United States",
        "region": "North America",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "government_database",
    },
    "arxiv.org": {
        "name": "arXiv",
        "country": "United States",
        "region": "North America",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "preprint_server",
    },
    "jstor.org": {
        "name": "JSTOR",
        "country": "United States",
        "region": "North America",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "digital_library",
    },
    "springer.com": {
        "name": "Springer Link",
        "country": "Germany",
        "region": "Europe",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "academic_publisher",
    },
    "link.springer.com": {
        "name": "Springer Link",
        "country": "Germany",
        "region": "Europe",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "academic_publisher",
    },
    "wiley.com": {
        "name": "Wiley Online Library",
        "country": "United States",
        "region": "North America",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "academic_publisher",
    },
    "ieee.org": {
        "name": "IEEE Xplore",
        "country": "United States",
        "region": "North America",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "academic_publisher",
    },
    "frontiersin.org": {
        "name": "Frontiers Media",
        "country": "Switzerland",
        "region": "Europe",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "open_access_publisher",
    },
    "plos.org": {
        "name": "PLOS ONE",
        "country": "United States",
        "region": "North America",
        "political_leaning": "academic/neutral",
        "reliability": "academic/peer-reviewed",
        "default_language": "English",
        "type": "open_access_publisher",
    },
    "britannica.com": {
        "name": "Encyclopædia Britannica",
        "country": "United Kingdom",
        "region": "Europe",
        "political_leaning": "center",
        "reliability": "high",
        "default_language": "English",
        "type": "encyclopedia",
    },
    "archive.org": {
        "name": "Internet Archive",
        "country": "United States",
        "region": "North America",
        "political_leaning": "neutral",
        "reliability": "high",
        "default_language": "English",
        "type": "digital_archive",
    },
}

# TLD & ccTLD Mappings for Fallback Geography
TLD_GEOGRAPHY_MAP: dict[str, tuple[str, str]] = {
    ".uk": ("United Kingdom", "Europe"),
    ".co.uk": ("United Kingdom", "Europe"),
    ".gov.uk": ("United Kingdom", "Europe"),
    ".de": ("Germany", "Europe"),
    ".fr": ("France", "Europe"),
    ".ca": ("Canada", "North America"),
    ".us": ("United States", "North America"),
    ".gov": ("United States", "North America"),
    ".edu": ("United States", "North America"),
    ".mil": ("United States", "North America"),
    ".au": ("Australia", "Oceania"),
    ".jp": ("Japan", "Asia"),
    ".cn": ("China", "Asia"),
    ".in": ("India", "Asia"),
    ".br": ("Brazil", "South America"),
    ".mx": ("Mexico", "North America"),
    ".ru": ("Russia", "Europe"),
    ".it": ("Italy", "Europe"),
    ".es": ("Spain", "Europe"),
    ".nl": ("Netherlands", "Europe"),
    ".se": ("Sweden", "Europe"),
    ".no": ("Norway", "Europe"),
    ".fi": ("Finland", "Europe"),
    ".pl": ("Poland", "Europe"),
    ".ua": ("Ukraine", "Europe"),
    ".za": ("South Africa", "Africa"),
    ".kr": ("South Korea", "Asia"),
    ".tw": ("Taiwan", "Asia"),
    ".sg": ("Singapore", "Asia"),
    ".hk": ("Hong Kong", "Asia"),
    ".il": ("Israel", "Middle East"),
    ".ae": ("United Arab Emirates", "Middle East"),
    ".sa": ("Saudi Arabia", "Middle East"),
    ".eg": ("Egypt", "Africa"),
    ".ng": ("Nigeria", "Africa"),
    ".ke": ("Kenya", "Africa"),
    ".nz": ("New Zealand", "Oceania"),
    ".ie": ("Ireland", "Europe"),
    ".ch": ("Switzerland", "Europe"),
    ".at": ("Austria", "Europe"),
    ".be": ("Belgium", "Europe"),
}

# Multilingual Name Gender Database
MULTILINGUAL_GENDER_NAMES: dict[str, dict[str, set[str]]] = {
    "English": {
        "female": {
            "jane", "mary", "susan", "sarah", "elizabeth", "emily", "jessica", "amanda", "ashley", "jennifer",
            "patricia", "linda", "barbara", "margaret", "lisa", "nancy", "karen", "betty", "helen", "sandra",
            "donna", "carol", "ruth", "sharon", "michelle", "laura", "rebecca", "cynthia", "kathleen", "amy",
            "angela", "shirley", "anna", "brenda", "pamela", "emma", "olivia", "sophia", "isabella", "charlotte"
        },
        "male": {
            "john", "michael", "david", "robert", "james", "joseph", "william", "richard", "thomas", "charles",
            "christopher", "daniel", "matthew", "anthony", "mark", "donald", "steven", "paul", "andrew", "joshua",
            "kenneth", "kevin", "brian", "george", "edward", "ronald", "timothy", "jason", "jeffrey", "ryan",
            "jacob", "gary", "nicholas", "eric", "jonathan", "alexander", "benjamin", "samuel", "stephen", "patrick"
        }
    },
    "French": {
        "female": {
            "marie", "sophie", "claire", "camille", "isabelle", "nathalie", "chantal", "francesca", "lea", "manon",
            "chloe", "oceane", "sarah", "emma", "ines", "jade", "louise", "alice", "lola", "amelie", "aurelie",
            "celine", "emmanuelle", "florence", "helene", "laurence", "sandrine", "valerie", "virginie", "brigitte"
        },
        "male": {
            "jean", "pierre", "michel", "philippe", "nicolas", "alexandre", "guillaume", "julien", "vincent", "thomas",
            "antoine", "lucas", "hugo", "enzo", "mathieu", "romain", "sebastien", "frederic", "olivier", "christophe",
            "laurent", "stephane", "david", "francois", "bernard", "didier", "alain", "christian", "eric", "emmanuel"
        }
    },
    "German": {
        "female": {
            "anna", "maria", "sabine", "ursula", "monika", "petra", "elisabeth", "susanne", "gabriele", "kristin",
            "gisela", "renate", "brigitte", "helga", "karin", "erika", "christa", "ingrid", "hannelore", "jutta",
            "leonie", "mia", "hannah", "emilia", "sofia", "lina", "mila", "emma", "klara", "martha", "hildegard"
        },
        "male": {
            "hans", "klaus", "peter", "dieter", "wolfgang", "jürgen", "günter", "walter", "heinz", "karl",
            "helmut", "gerhard", "werner", "uwe", "frank", "thomas", "andreas", "michael", "stefan", "christian",
            "maximilian", "alexander", "paul", "leon", "jonas", "ben", "elias", "luka", "felix", "moritz"
        }
    },
    "Spanish": {
        "female": {
            "maria", "carmen", "ana", "isabel", "dolores", "pilar", "teresa", "josefa", "beatriz", "laura",
            "cristina", "marta", "sofia", "lucia", "martina", "sara", "paula", "elena", "alba", "claudia",
            "juana", "francisca", "antonia", "luisa", "concepcion", "mercedes", "monica", "silvia", "patricia"
        },
        "male": {
            "juan", "manuel", "jose", "francisco", "antonio", "david", "javier", "daniel", "carlos", "jesus",
            "alejandro", "miguel", "rafael", "pedro", "angel", "pablo", "fernando", "jorge", "luis", "alberto",
            "hugo", "lucas", "mateo", "martin", "adrian", "alvaro", "diego", "sergio", "marcos", "santiago"
        }
    },
    "Italian": {
        "female": {
            "giulia", "sofia", "aurora", "alice", "emma", "giorgia", "chiara", "francesca", "federica", "sara",
            "anna", "maria", "giovanna", "rosa", "angela", "luisa", "elena", "silvia", "laura", "paola",
            "alessandra", "valentina", "cristina", "simona", "antonella", "roberta", "daniela", "marina", "elisa"
        },
        "male": {
            "francesco", "alessandro", "lorenzo", "mattia", "andrea", "gabriele", "riccardo", "giuseppe", "antonio", "giovanni",
            "marco", "matteo", "leonardo", "davide", "simone", "federico", "filippo", "luca", "christian", "roberto",
            "stefano", "mario", "luigi", "salvatore", "vincenzo", "pietro", "paolo", "angelo", "emanuele", "michele"
        }
    },
    "Russian": {
        "female": {
            "elena", "olga", "natasha", "tatiana", "maria", "anna", "ekaterina", "svetlana", "irina", "anastasia",
            "julia", "daria", "ludmila", "galina", "valentina", "nina", "larisa", "marina", "sofia", "polina"
        },
        "male": {
            "sergei", "dmitry", "ivan", "vladimir", "alexander", "mikhail", "andrey", "alexey", "evgeny", "nikolay",
            "yury", "artyom", "maxim", "kirill", "danila", "egor", "ilya", "nikita", "pavel", "anton"
        }
    },
    "Arabic": {
        "female": {
            "fatima", "aisha", "zainab", "maryam", "khadija", "yasmin", "amira", "layla", "farah", "noor",
            "salma", "reem", "mona", "hoda", "nadia", "rana", "maha", "sara", "lina", "amal"
        },
        "male": {
            "mohammed", "muhammad", "ahmed", "ali", "hassan", "hussein", "omar", "youssef", "mustafa", "khalid",
            "tarek", "karim", "ibrahim", "mahmoud", "saeed", "faisal", "ziad", "nabil", "ramy", "samir"
        }
    },
    "Indian": {
        "female": {
            "priya", "sunita", "anita", "pooja", "neha", "deepika", "jyoti", "aishwarya", "divya", "kiran",
            "meena", "rekha", "sushma", "harpreet", "jaspreet", "swati", "anjali", "ritika", "shruthi", "kavita"
        },
        "male": {
            "rahul", "amit", "rajesh", "sanjay", "vijay", "ajay", "abhishek", "vikram", "rohit", "sandeep",
            "harpreet", "jaspreet", "kumar", "singh", "anand", "arjun", "aditya", "manish", "anil", "sunil"
        }
    },
    "Chinese": {
        "female": {
            "mei", "ling", "fang", "yan", "li", "ting", "jing", "min", "xia", "hong",
            "lan", "ying", "hua", "zhen", "yun", "wen", "qian", "jia", "yi", "hui"
        },
        "male": {
            "wei", "jun", "yong", "jie", "jian", "qiang", "guo", "hao", "bo", "gang",
            "ming", "zhi", "hui", "dong", "xiang", "bin", "chao", "lei", "feng", "yu"
        }
    },
    "Japanese": {
        "female": {
            "yuki", "sakura", "haruka", "aoi", "yui", "hina", "mei", "mio", "misaki", "nanami",
            "yoko", "keiko", "hiromi", "naoko", "atsuko", "mayumi", "ayumi", "kaori", "mariko", "chiyo"
        },
        "male": {
            "hiroshi", "kenji", "takashi", "yuto", "haruto", "sota", "ren", "yamato", "riku", "kaito",
            "shigeru", "akira", "yoshio", "kazuo", "tomasu", "taro", "ichiro", "jiro", "saburo", "ken"
        }
    }
}

FIRST_NAME_GENDER: dict[str, str] = {}
for lang, genders in MULTILINGUAL_GENDER_NAMES.items():
    for gender, names in genders.items():
        for name in names:
            FIRST_NAME_GENDER[name] = gender

# Name Origin & Linguistic Heuristics
SURNAME_ORIGIN_PATTERNS: list[tuple[str, str, str]] = [
    # (Regex pattern, Country hint, Region hint)
    (r"\b(mac|mc)[a-z]+", "United Kingdom", "Europe"),  # Scottish/Irish
    (r"\b(o')[a-z]+", "Ireland", "Europe"),
    (r"\b[a-z]+(ov|ova|ev|eva|sky|ski)$", "Russia/Eastern Europe", "Europe"),
    (r"\b(van|von|den|der)\s+[a-z]+", "Netherlands/Germany", "Europe"),
    (r"\b(de|di|d')\s+[a-z]+", "France/Italy/Spain", "Europe"),
    (r"\b[a-z]+(ez|az)$", "Spain/Latin America", "South/Central America"),
    (r"\b(chen|wang|zhang|li|liu|yang|huang|wu|zhao|zhou|xu|sun|ma|zhu)\b", "China", "Asia"),
    (r"\b(singh|kumar|kaur|sharma|patel|gupta|rao|reddy|joshi|verma|nair)\b", "India", "Asia"),
    (r"\b(tanaka|sato|suzuki|takahashi|watanabe|ito|yamamoto|nakamura|kobayashi)\b", "Japan", "Asia"),
    (r"\b(kim|park|lee|choi|jeong|kang|cho|yoon|jang|lim)\b", "South Korea", "Asia"),
    (r"\b(al-|el-)[a-z]+", "Middle East/North Africa", "Middle East"),
]

# Multilingual Loaded Language Lexicons
MULTILINGUAL_LOADED_WORDS: dict[str, set[str]] = {
    "English": {
        "outrageous", "shocking", "scandalous", "unquestionably", "disastrous", "tyrant",
        "regime", "mastermind", "slammed", "blasted", "heroic", "despicable", "infamous",
        "purported", "alleged", "so-called", "fanatic", "extremist", "radical", "spectacular",
        "catastrophic", "fraudulent", "puppet", "propaganda", "corrupt", "atrocity",
        "courageous", "monstrous", "hypocritical", "sham", "ruthless", "cynical"
    },
    "French": {
        "scandaleux", "choquant", "désastreux", "tyran", "régime", "fustigé", "attaqué",
        "héroïque", "méprisable", "infâme", "prétendu", "allégué", "soi-disant", "fanatique",
        "extrémiste", "radical", "spectaculaire", "catastrophique", "frauduleux", "marionnette",
        "propagande", "corrompu", "atrocité", "courageux", "monstrueux", "hypocrite",
        "imposture", "impitoyable", "cynique"
    },
    "German": {
        "skandalös", "schockierend", "katastrophal", "tyrann", "regime", "kritisierte",
        "angegriffen", "heldenhaft", "verabscheuungswürdig", "berüchtigt", "angeblich",
        "sogenannt", "fanatisch", "extremistisch", "radikal", "spektakulär", "betrügerisch",
        "marionette", "propaganda", "korrupt", "grausamkeit", "mutig", "monströs",
        "scheinheilig", "scham", "rücksichtslos", "zynisch"
    },
    "Spanish": {
        "escandaloso", "sorprendente", "desastroso", "tirano", "régimen", "criticó",
        "atacó", "heroico", "despreciable", "infame", "pretendido", "presunto", "llamado",
        "fanático", "extremista", "radical", "espectacular", "catastrófico", "fraudulento",
        "títere", "propaganda", "corrupto", "atrocidad", "valiente", "monstruoso",
        "hipócrita", "farsa", "despiadado", "cínico"
    },
    "Italian": {
        "scandaloso", "scioccante", "disastroso", "tiranno", "regime", "criticato",
        "attaccato", "eroico", "disprezzabile", "infame", "presunto", "cosiddetto",
        "fanatico", "estremista", "radicale", "spettacolare", "catastrofico", "fraudolento",
        "marionetta", "propaganda", "corrotto", "atrocità", "coraggioso", "mostruoso",
        "ipocrita", "farsa", "spietato", "cinico"
    }
}

MULTILINGUAL_OPINION_INDICATORS: dict[str, set[str]] = {
    "English": {
        "opinion", "editorial", "column", "commentary", "op-ed", "essay", "analysis",
        "thoughts", "argument", "perspective", "viewpoint"
    },
    "French": {
        "opinion", "éditorial", "tribune", "commentaire", "analyse", "chronique",
        "perspective", "point de vue", "tribunes", "débats", "debat", "debats"
    },
    "German": {
        "meinung", "editorial", "kommentar", "analyse", "kolumne", "standpunkt",
        "perspektive"
    },
    "Spanish": {
        "opinión", "editorial", "columna", "comentario", "análisis", "tribuna",
        "perspectiva", "punto de vista"
    },
    "Italian": {
        "opinione", "editoriale", "rubrica", "commento", "analisi", "prospettiva",
        "punto di vista"
    }
}

SUBJECTIVE_LOADED_WORDS: set[str] = set()
for words in MULTILINGUAL_LOADED_WORDS.values():
    SUBJECTIVE_LOADED_WORDS.update(words)

OPINION_EDITORIAL_INDICATORS: set[str] = set()
for indicators in MULTILINGUAL_OPINION_INDICATORS.values():
    OPINION_EDITORIAL_INDICATORS.update(indicators)
