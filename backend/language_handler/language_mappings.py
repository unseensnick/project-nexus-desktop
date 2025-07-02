"""
Language mappings and ISO standards for language code normalization.

Contains comprehensive mappings between different language code formats,
regional variants, and common language names to enable robust language detection.
"""

from typing import Dict, List, Set

# ISO 639-1 (2-letter) to ISO 639-2 (3-letter) mapping
ISO_639_1_TO_639_2: Dict[str, str] = {
    "ar": "ara",  # Arabic
    "zh": "zho",  # Chinese
    "cs": "ces",  # Czech
    "nl": "nld",  # Dutch
    "en": "eng",  # English
    "fi": "fin",  # Finnish
    "fr": "fra",  # French
    "de": "deu",  # German
    "el": "ell",  # Greek
    "he": "heb",  # Hebrew
    "hi": "hin",  # Hindi
    "hu": "hun",  # Hungarian
    "id": "ind",  # Indonesian
    "it": "ita",  # Italian
    "ja": "jpn",  # Japanese
    "ko": "kor",  # Korean
    "no": "nor",  # Norwegian
    "fa": "fas",  # Persian
    "pl": "pol",  # Polish
    "pt": "por",  # Portuguese
    "ro": "ron",  # Romanian
    "ru": "rus",  # Russian
    "sr": "srp",  # Serbian
    "sk": "slk",  # Slovak
    "es": "spa",  # Spanish
    "sv": "swe",  # Swedish
    "th": "tha",  # Thai
    "tr": "tur",  # Turkish
    "uk": "ukr",  # Ukrainian
    "vi": "vie",  # Vietnamese
}

# Reverse mapping for lookups
ISO_639_2_TO_639_1: Dict[str, str] = {v: k for k, v in ISO_639_1_TO_639_2.items()}

# Alternative ISO 639-2 codes (bibliographic vs. terminological)
ALTERNATIVE_ISO_639_2: Dict[str, str] = {
    "fre": "fra",  # French
    "ger": "deu",  # German
    "dut": "nld",  # Dutch
    "gre": "ell",  # Greek
    "chi": "zho",  # Chinese
    "cze": "ces",  # Czech
    "rum": "ron",  # Romanian
    "slo": "slk",  # Slovak
    "per": "fas",  # Persian
}

# Set of valid ISO 639-2 codes
VALID_ISO_639_2_CODES: Set[str] = set(ISO_639_1_TO_639_2.values()).union(set(ALTERNATIVE_ISO_639_2.values()))

# Comprehensive language mappings including variants and common names
LANGUAGE_MAPPINGS: Dict[str, List[str]] = {
    # English variations
    "eng": ["eng", "en", "english", "en-us", "en-gb", "en-ca", "en-au", "en_us", "en_gb"],
    
    # Japanese variations
    "jpn": ["jpn", "ja", "jp", "jap", "japanese", "日本語", "nihongo", "japones", "japon"],
    
    # Spanish variations
    "spa": ["spa", "es", "spanish", "español", "espanol", "castellano", "es-es", "es-mx", "es-419"],
    
    # French variations
    "fra": ["fra", "fre", "fr", "french", "français", "francais", "fr-fr", "fr-ca", "fr-be"],
    
    # German variations
    "deu": ["deu", "ger", "de", "german", "deutsch", "de-de", "de-at", "de-ch"],
    
    # Chinese variations
    "zho": ["zho", "chi", "zh", "chinese", "中文", "zhongwen", "mandarin", "zh-cn", "zh-tw"],
    
    # Italian variations
    "ita": ["ita", "it", "italian", "italiano", "it-it"],
    
    # Korean variations
    "kor": ["kor", "ko", "korean", "한국어", "kr", "hangul", "hangugeo"],
    
    # Russian variations
    "rus": ["rus", "ru", "russian", "русский", "russkiy"],
    
    # Portuguese variations
    "por": ["por", "pt", "portuguese", "português", "portugues", "pt-br", "pt-pt", "brazilian"],
    
    # Arabic variations
    "ara": ["ara", "ar", "arabic", "العربية", "al-arabiyyah"],
    
    # Dutch variations
    "nld": ["nld", "dut", "nl", "dutch", "nederlands"],
    
    # Hindi variations
    "hin": ["hin", "hi", "hindi", "हिन्दी"],
    
    # Swedish variations
    "swe": ["swe", "sv", "swedish", "svenska"],
    
    # Norwegian variations
    "nor": ["nor", "no", "norwegian", "norsk"],
    
    # Finnish variations
    "fin": ["fin", "fi", "finnish", "suomi"],
    
    # Danish variations
    "dan": ["dan", "da", "danish", "dansk"],
    
    # Czech variations
    "ces": ["ces", "cze", "cs", "czech", "čeština", "cestina"],
    
    # Polish variations
    "pol": ["pol", "pl", "polish", "polski"],
    
    # Special undefined code
    "und": ["und", "undefined", "unknown", "unspecified", ""],
}

# Reverse lookup table for fast variant recognition
LANGUAGE_CODE_LOOKUP: Dict[str, str] = {}
for standard_code, variations in LANGUAGE_MAPPINGS.items():
    for variant in variations:
        if variant:  # Skip empty strings
            LANGUAGE_CODE_LOOKUP[variant.lower()] = standard_code

# Human-readable language names
LANGUAGE_NAMES: Dict[str, str] = {
    "eng": "English",
    "jpn": "Japanese", 
    "spa": "Spanish",
    "fra": "French",
    "deu": "German",
    "zho": "Chinese",
    "ita": "Italian",
    "kor": "Korean",
    "rus": "Russian",
    "por": "Portuguese",
    "ara": "Arabic",
    "nld": "Dutch",
    "hin": "Hindi",
    "swe": "Swedish",
    "nor": "Norwegian",
    "fin": "Finnish",
    "dan": "Danish",
    "ces": "Czech",
    "pol": "Polish",
    "und": "Undefined"
}

def get_common_languages() -> List[str]:
    """
    Get list of commonly used language codes.
    
    Returns:
        List of ISO 639-2 codes for common languages
    """
    return [
        "eng",  # English
        "spa",  # Spanish
        "fra",  # French
        "deu",  # German
        "ita",  # Italian
        "jpn",  # Japanese
        "kor",  # Korean
        "zho",  # Chinese
        "rus",  # Russian
        "por",  # Portuguese
    ] 