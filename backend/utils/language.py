"""
Language Utilities Module.

Provides robust language identification, normalization, and validation for media tracks.
Simplifies working with language codes by:

- Standardizing diverse language formats (ISO codes, names, regional variants)
- Extracting language information from filenames and titles
- Supporting fallback detection when metadata is missing or ambiguous
- Filtering tracks by language preferences

All functions use ISO 639-2 (3-letter codes) as the standardized format internally,
with comprehensive mapping to handle common variations and user input flexibility.
"""

import logging
import re
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)
MODULE_NAME = "language_utils"

# =====================================================================
# ISO Standards Mappings
# =====================================================================

# ISO 639-1 (2-letter) to ISO 639-2 (3-letter) mapping for common languages
ISO_639_1_TO_639_2 = {
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
ISO_639_2_TO_639_1 = {v: k for k, v in ISO_639_1_TO_639_2.items()}

# Alternative ISO 639-2 codes (bibliographic vs. terminological)
ALTERNATIVE_ISO_639_2 = {
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

# Set of valid ISO 639-2 codes for validation
VALID_ISO_639_2_CODES = set(ISO_639_1_TO_639_2.values()).union(set(ALTERNATIVE_ISO_639_2.values()))

# =====================================================================
# Extended Language Mappings (Common Variations and Aliases)
# =====================================================================

# Mapping from standard codes to all possible variants (names, codes, regional variants)
LANGUAGE_MAPPINGS = {
    # ---- English Variations ----
    "eng": ["eng", "en", "english", "en-us", "en-gb", "en-ca", "en-au", "en_us", "en_gb"],
    
    # ---- Japanese Variations ----
    "jpn": ["jpn", "ja", "jp", "jap", "japanese", "日本語", "nihongo", "japones", "japon"],

    # ---- Spanish Variations ----
    "spa": ["spa", "es", "spanish", "español", "espanol", "castellano", "es-es", "es-mx", "es-419"],
    
    # ---- French Variations ----
    "fra": ["fra", "fre", "fr", "french", "français", "francais", "fr-fr", "fr-ca", "fr-be"],
    
    # ---- German Variations ----
    "deu": ["deu", "ger", "de", "german", "deutsch", "de-de", "de-at", "de-ch"],
    
    # ---- Chinese Variations ----
    "zho": ["zho", "chi", "zh", "chinese", "中文", "zhongwen", "mandarin", "zh-cn", "zh-tw"],
    
    # ---- Italian Variations ----
    "ita": ["ita", "it", "italian", "italiano", "it-it"],
    
    # ---- Korean Variations ----
    "kor": ["kor", "ko", "korean", "한국어", "kr", "hangul", "hangugeo"],
    
    # ---- Russian Variations ----
    "rus": ["rus", "ru", "russian", "русский", "russkiy"],
    
    # ---- Portuguese Variations ----
    "por": ["por", "pt", "portuguese", "português", "portugues", "pt-br", "pt-pt", "brazilian"],
    
    # ---- Arabic Variations ----
    "ara": ["ara", "ar", "arabic", "العربية", "al-arabiyyah"],
    
    # ---- Other Languages ----
    "nld": ["nld", "dut", "nl", "dutch", "nederlands"],  # Dutch
    "hin": ["hin", "hi", "hindi", "हिन्दी"],  # Hindi
    "swe": ["swe", "sv", "swedish", "svenska"],  # Swedish
    "nor": ["nor", "no", "norwegian", "norsk"],  # Norwegian
    "fin": ["fin", "fi", "finnish", "suomi"],  # Finnish
    "dan": ["dan", "da", "danish", "dansk"],  # Danish
    "ces": ["ces", "cze", "cs", "czech", "čeština", "cestina"],  # Czech
    "pol": ["pol", "pl", "polish", "polski"],  # Polish
    
    # ---- Special Codes ----
    "und": ["und", "undefined", "unknown", "unspecified", ""],  # Undefined
}

# Reverse lookup table for fast variant recognition
LANGUAGE_CODE_LOOKUP = {}
for standard_code, variations in LANGUAGE_MAPPINGS.items():
    for variant in variations:
        if variant:  # Skip empty strings
            LANGUAGE_CODE_LOOKUP[variant.lower()] = standard_code

# =====================================================================
# Filename and Title Pattern Matching
# =====================================================================

# Common patterns to identify languages in filenames
FILENAME_LANGUAGE_PATTERNS = [
    # Match [lang] or (lang) formats
    (r'[\[\(]((?:en|eng|english|eng?lish))[\]\)]', "eng"),
    (r'[\[\(]((?:jp|jpn|ja|jap|japanese))[\]\)]', "jpn"),
    (r'[\[\(]((?:es|spa|spanish|español|espanol))[\]\)]', "spa"),
    (r'[\[\(]((?:fr|fra|fre|french|français|francais))[\]\)]', "fra"),
    (r'[\[\(]((?:de|deu|ger|german|deutsch))[\]\)]', "deu"),
    (r'[\[\(]((?:zh|zho|chi|cn|chinese))[\]\)]', "zho"),
    (r'[\[\(]((?:it|ita|italian|italiano))[\]\)]', "ita"),
    (r'[\[\(]((?:ko|kor|korean))[\]\)]', "kor"),
    (r'[\[\(]((?:ru|rus|russian))[\]\)]', "rus"),
    
    # Match .lang. format in filenames
    (r'\.([a-z]{2,3})\.(srt|ass|ssa|sub|idx|vtt|mks|ac3|aac|mp3|mka|mkv|mp4)$', None),
    
    # Match _lang_, .lang., -lang- formats
    (r'[._-]([a-z]{2,3})[._-]', None),
    
    # Match _language_, .language. formats
    (r'[._-](english|spanish|french|german|italian|japanese|korean|chinese|russian)[._-]', None),
]

# Language names in various languages for matching in titles
LANGUAGE_NAMES = {
    "eng": ["English", "Inglés", "Anglais"],
    "spa": ["Spanish", "Español", "Espagnol", "Castellano"],
    "fra": ["French", "Francés", "Français"],
    "deu": ["German", "Alemán", "Deutsch", "Allemand"],
    "ita": ["Italian", "Italiano", "Italien"],
    "jpn": ["Japanese", "Japonés", "Japonais", "日本語"],
    "zho": ["Chinese", "Chino", "Chinois", "中文"],
    "kor": ["Korean", "Coreano", "Coréen", "한국어"],
    "rus": ["Russian", "Ruso", "Russe", "Русский"],
}

# =====================================================================
# Core Language Functions
# =====================================================================

def normalize_language_code(code: str) -> Optional[str]:
    """
    Convert any language identifier to standard ISO 639-2 format.
    
    Handles diverse inputs including:
    - 2-letter ISO 639-1 codes (en, fr)
    - 3-letter ISO 639-2 codes (eng, fra)
    - Alternative 3-letter codes (fre instead of fra)
    - Language names in English and other languages
    - Regional variants with country codes (en-us, pt-br)
    
    Args:
        code: Language identifier to normalize (code or name)

    Returns:
        Standard 3-letter ISO 639-2 code, or None if unrecognized
    """
    if not code:
        return None

    # Clean up the code
    clean_code = code.lower().strip()

    # Direct lookup in our mapping
    if clean_code in LANGUAGE_CODE_LOOKUP:
        return LANGUAGE_CODE_LOOKUP[clean_code]

    # Try ISO 639-1 to ISO 639-2 conversion
    if len(clean_code) == 2 and clean_code in ISO_639_1_TO_639_2:
        return ISO_639_1_TO_639_2[clean_code]

    # Try alternative ISO 639-2 codes
    if clean_code in ALTERNATIVE_ISO_639_2:
        return ALTERNATIVE_ISO_639_2[clean_code]

    # If it's already a valid ISO 639-2 code
    if len(clean_code) == 3 and clean_code in VALID_ISO_639_2_CODES:
        return clean_code

    # Handle country code suffixes (e.g., en-us, pt-br)
    if "-" in clean_code or "_" in clean_code:
        base_code = re.split(r'[-_]', clean_code)[0]
        return normalize_language_code(base_code)

    # If we get here, we can't normalize the code
    logger.debug(f"Could not normalize language code: {code}")
    return None


def detect_language_from_filename(filename: str) -> Optional[str]:
    """
    Extract language information from a filename using pattern recognition.
    
    Searches for common language indicators in filenames such as:
    - [en] or (eng) markers
    - .eng. separators in the filename
    - _english_ text patterns
    
    Args:
        filename: File name to analyze

    Returns:
        Normalized 3-letter ISO code if detected, None otherwise
    """
    if not filename:
        return None
    
    filename_lower = filename.lower()

    # Try each pattern
    for pattern, fixed_code in FILENAME_LANGUAGE_PATTERNS:
        match = re.search(pattern, filename_lower)
        if match:
            if fixed_code:
                # Pattern has a fixed language code
                return fixed_code
            else:
                # Extract and normalize the language code from the match
                potential_code = match.group(1)
                normalized_code = normalize_language_code(potential_code)
                if normalized_code:
                    logger.debug(f"Detected language '{normalized_code}' from filename '{filename}'")
                    return normalized_code

    return None


def detect_language_from_title(title: str) -> Optional[str]:
    """
    Extract language information from track title metadata.
    
    Searches for language indicators in title fields such as:
    - Language names in various languages ("English", "Español")
    - Language codes in brackets [en], [eng], etc.
    
    Args:
        title: Track title text to analyze

    Returns:
        Normalized 3-letter ISO code if detected, None otherwise
    """
    if not title:
        return None
    
    title_lower = title.lower()
    
    # Try to match language names in title
    for lang_code, names in LANGUAGE_NAMES.items():
        for name in names:
            if name.lower() in title_lower:
                logger.debug(f"Detected language '{lang_code}' from title '{title}'")
                return lang_code
                
    # Try to match language codes in brackets [en], [eng], etc.
    match = re.search(r'\[((?:en|eng|es|spa|fr|fra|de|deu|it|ita|jp|jpn|zh|zho|ko|kor|ru|rus))\]', title_lower)
    if match:
        potential_code = match.group(1)
        normalized_code = normalize_language_code(potential_code)
        if normalized_code:
            logger.debug(f"Detected language code '{normalized_code}' from title bracket '[{potential_code}]'")
            return normalized_code
    
    return None


def enhance_language_detection(
    metadata_lang: Optional[str], 
    filename: str, 
    track_title: Optional[str] = None
) -> Optional[str]:
    """
    Determine track language through layered detection strategies.
    
    Applies multiple detection methods in priority order:
    1. File metadata (if available)
    2. Track title analysis (if available)
    3. Filename pattern matching
    4. Default to "und" (undefined) as last resort
    
    This multi-layered approach maximizes accuracy when metadata
    is missing or inconsistent.

    Args:
        metadata_lang: Language from file metadata (may be None)
        filename: Filename for pattern analysis
        track_title: Track title for additional detection (may be None)

    Returns:
        Normalized 3-letter ISO code or "und" for undefined
    """
    # Try metadata first
    if metadata_lang:
        normalized = normalize_language_code(metadata_lang)
        if normalized:
            logger.debug(f"Using metadata language: {metadata_lang} -> {normalized}")
            return normalized

    # Try track title if available
    if track_title:
        lang_from_title = detect_language_from_title(track_title)
        if lang_from_title:
            logger.debug(f"Using language from title: {lang_from_title}")
            return lang_from_title

    # Fall back to filename analysis
    lang_from_filename = detect_language_from_filename(filename)
    if lang_from_filename:
        logger.debug(f"Using language from filename: {lang_from_filename}")
        return lang_from_filename
        
    # Last resort - if no language detected, return undefined
    return "und"


def is_valid_language_code(code: str) -> bool:
    """
    Verify if a language code can be recognized and normalized.
    
    Useful for validating user input or configuration before processing.

    Args:
        code: Language code or name to validate

    Returns:
        True if code can be normalized to a valid ISO 639-2 code
    """
    if not code:
        return False

    normalized = normalize_language_code(code)
    return normalized is not None


def get_common_languages() -> List[str]:
    """
    Get standardized codes for the most commonly used languages.
    
    Provides a default set of popular languages for UI display
    or default filter options.

    Returns:
        List of common ISO 639-2 language codes in order of popularity
    """
    # Return most common languages first
    return [
        "eng",  # English
        "spa",  # Spanish
        "fra",  # French
        "deu",  # German
        "ita",  # Italian
        "jpn",  # Japanese
        "zho",  # Chinese
        "kor",  # Korean
        "rus",  # Russian
        "por",  # Portuguese
        "ara",  # Arabic
        "nld",  # Dutch
        "hin",  # Hindi
        "swe",  # Swedish
    ]


def normalize_language_codes(
    language_codes: Union[str, List[str]], 
    remove_duplicates: bool = True
) -> List[str]:
    """
    Normalize multiple language codes in a batch operation.
    
    Handles both single codes and lists, with options for deduplication.
    Failed normalizations are kept as lowercase originals to preserve intent.

    Args:
        language_codes: Single code or list of codes to normalize
        remove_duplicates: Whether to remove duplicates after normalization

    Returns:
        List of normalized codes (or original lowercase if normalization failed)
    """
    # Convert single code to list
    if isinstance(language_codes, str):
        codes_list = [language_codes]
    else:
        codes_list = language_codes
        
    # Normalize each code
    normalized_codes = []
    for code in codes_list:
        if not code:
            continue
            
        norm_code = normalize_language_code(code)
        if norm_code:
            normalized_codes.append(norm_code)
        else:
            # Keep original code if normalization fails
            logger.warning(f"Could not normalize language code: {code}")
            normalized_codes.append(code.lower())
            
    # Remove duplicates if requested
    if remove_duplicates:
        return list(dict.fromkeys(normalized_codes))  # Preserves order
        
    return normalized_codes
    

def filter_by_languages(
    all_items: List[Dict], 
    requested_languages: List[str], 
    lang_key: str = "language",
    include_undefined: bool = False
) -> List[Dict]:
    """
    Filter a list of items based on language criteria.
    
    Selects items whose language matches any of the requested languages.
    Handles normalization of both requested languages and item languages.

    Args:
        all_items: List of dicts with language information
        requested_languages: Languages to keep (normalized internally)
        lang_key: Dictionary key containing the language value
        include_undefined: Whether to include items with missing/empty language

    Returns:
        Filtered list containing only items with matching languages
    """
    if not all_items:
        return []
        
    if not requested_languages:
        return all_items
        
    # Normalize requested languages
    norm_requested = normalize_language_codes(requested_languages)
    
    # Add 'und' if requested
    if include_undefined:
        norm_requested.append("und")
        
    logger.debug(f"Filtering items by languages: {norm_requested}")
    
    # Filter items
    filtered_items = []
    for item in all_items:
        # Handle items with no language
        item_lang = item.get(lang_key)
        if not item_lang:
            if include_undefined:
                filtered_items.append(item)
            continue
            
        # Normalize item language
        norm_item_lang = normalize_language_code(item_lang) or item_lang.lower()
        
        # Include if language matches
        if norm_item_lang in norm_requested:
            filtered_items.append(item)
            
    return filtered_items


def get_language_name(code: str) -> str:
    """
    Get human-readable language name from language code.
    
    Transforms technical codes into user-friendly display names.

    Args:
        code: Language code (ISO 639-1 or ISO 639-2)

    Returns:
        Human-readable language name, or original code if unrecognized
    """
    normalized = normalize_language_code(code)
    if not normalized:
        return code

    # Map from ISO 639-2 to language names
    language_names = {
        "eng": "English",
        "spa": "Spanish",
        "fra": "French",
        "deu": "German",
        "ita": "Italian",
        "jpn": "Japanese",
        "zho": "Chinese",
        "kor": "Korean",
        "rus": "Russian",
        "ara": "Arabic",
        "por": "Portuguese",
        "nld": "Dutch",
        "hin": "Hindi",
        "swe": "Swedish",
        "nor": "Norwegian",
        "fin": "Finnish",
        "dan": "Danish",
        "ces": "Czech",
        "pol": "Polish",
        "ell": "Greek",
        "heb": "Hebrew",
        "hun": "Hungarian",
        "ind": "Indonesian",
        "ron": "Romanian",
        "srp": "Serbian",
        "slk": "Slovak",
        "tha": "Thai",
        "tur": "Turkish",
        "ukr": "Ukrainian",
        "vie": "Vietnamese",
        "und": "Unknown",
    }

    return language_names.get(normalized, code)


def create_language_filter(
    requested_languages: List[str], 
    include_undefined: bool = False
) -> callable:
    """
    Create a reusable filter function for language matching.
    
    Returns a function that can be used multiple times to test
    if language codes match the specified criteria.

    Args:
        requested_languages: List of languages to match against
        include_undefined: Whether to accept undefined languages

    Returns:
        Function that takes a language code and returns True if it matches
    """
    # Normalize requested languages for consistent comparison
    norm_requested = normalize_language_codes(requested_languages)
    
    # Add 'und' to the accepted languages if requested
    if include_undefined:
        norm_requested.append("und")
        
    def language_filter(language_code: Optional[str]) -> bool:
        """
        Test if a language code matches the filter criteria.
        """
        # Handle undefined language
        if not language_code or language_code.lower() in ("und", "unknown", ""):
            return include_undefined
            
        # Normalize and compare
        norm_lang = normalize_language_code(language_code) or language_code.lower()
        return norm_lang in norm_requested
        
    return language_filter