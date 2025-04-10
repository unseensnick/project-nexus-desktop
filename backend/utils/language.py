"""
Language Utilities Module.

This module provides utilities for language code detection, normalization, and validation.
It enhances the reliability of language detection for media tracks by supporting multiple
language code formats and implementing fallback detection strategies.
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# ISO 639-1 to ISO 639-2 mapping (common languages)
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

# Reverse mapping
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

# Common language name variations and misspellings
LANGUAGE_NAME_TO_CODE = {
    # English variations
    "english": "eng",
    "eng": "eng",
    "en": "eng",
    "en-us": "eng",
    "en-gb": "eng",
    "en-au": "eng",
    # Spanish variations
    "spanish": "spa",
    "espanol": "spa",
    "español": "spa",
    "spa": "spa",
    "es": "spa",
    "es-es": "spa",
    "es-mx": "spa",
    "castellano": "spa",
    # French variations
    "french": "fra",
    "français": "fra",
    "francais": "fra",
    "fra": "fra",
    "fre": "fra",
    "fr": "fra",
    "fr-fr": "fra",
    "fr-ca": "fra",
    # German variations
    "german": "deu",
    "deutsch": "deu",
    "deu": "deu",
    "ger": "deu",
    "de": "deu",
    "de-de": "deu",
    # Italian variations
    "italian": "ita",
    "italiano": "ita",
    "ita": "ita",
    "it": "ita",
    "it-it": "ita",
    # Japanese variations
    "japanese": "jpn",
    "日本語": "jpn",
    "nihongo": "jpn",
    "jpn": "jpn",
    "ja": "jpn",
    "jp": "jpn",
    # Chinese variations
    "chinese": "zho",
    "中文": "zho",
    "zhongwen": "zho",
    "mandarin": "zho",
    "zho": "zho",
    "chi": "zho",
    "zh": "zho",
    "zh-cn": "zho",
    "zh-tw": "zho",
    # Korean variations
    "korean": "kor",
    "한국어": "kor",
    "hangugeo": "kor",
    "kor": "kor",
    "ko": "kor",
    "kr": "kor",
    # Russian variations
    "russian": "rus",
    "русский": "rus",
    "russkiy": "rus",
    "rus": "rus",
    "ru": "rus",
    # Arabic variations
    "arabic": "ara",
    "العربية": "ara",
    "al-arabiyyah": "ara",
    "ara": "ara",
    "ar": "ara",
    # Portuguese variations
    "portuguese": "por",
    "português": "por",
    "portugues": "por",
    "por": "por",
    "pt": "por",
    "pt-br": "por",
    "pt-pt": "por",
    "brazilian": "por",
    # Dutch variations
    "dutch": "nld",
    "nederlands": "nld",
    "nld": "nld",
    "dut": "nld",
    "nl": "nld",
    # Hindi variations
    "hindi": "hin",
    "हिन्दी": "hin",
    "hin": "hin",
    "hi": "hin",
    # Swedish variations
    "swedish": "swe",
    "svenska": "swe",
    "swe": "swe",
    "sv": "swe",
    # Norwegian variations
    "norwegian": "nor",
    "norsk": "nor",
    "nor": "nor",
    "no": "nor",
    # Finnish variations
    "finnish": "fin",
    "suomi": "fin",
    "fin": "fin",
    "fi": "fin",
    # Danish variations
    "danish": "dan",
    "dansk": "dan",
    "dan": "dan",
    "da": "dan",
    # Czech variations
    "czech": "ces",
    "čeština": "ces",
    "cestina": "ces",
    "ces": "ces",
    "cze": "ces",
    "cs": "ces",
    # Polish variations
    "polish": "pol",
    "polski": "pol",
    "pol": "pol",
    "pl": "pol",
    # Unknown/undetermined
    "unknown": "und",
    "undetermined": "und",
    "und": "und",
    "undefined": "und",
}

# Set of valid ISO 639-2 codes for validation
VALID_ISO_639_2_CODES = set(ISO_639_1_TO_639_2.values()) | set(
    ALTERNATIVE_ISO_639_2.values()
)

# Common language patterns in filenames
FILENAME_LANGUAGE_PATTERNS = [
    # Match .en.srt, .eng.srt, etc.
    (r"\.([a-z]{2,3})\.(srt|ass|ssa|sub|idx|vtt|mks|ac3|aac|dts|mp3|m4a|flac)$", 1),
    # Match _en_, .en., -en-, etc.
    (r"[._-]([a-z]{2,3})[._-]", 1),
    # Match _english_, .english., etc.
    (
        r"[._-](english|spanish|french|german|italian|japanese|korean|chinese|russian|arabic|portuguese|dutch|hindi|swedish)[._-]",
        1,
    ),
    # Match _eng_, .spa., etc.
    (r"[._-](eng|spa|fra|deu|ita|jpn|kor|zho|rus|ara|por|nld|hin|swe)[._-]", 1),
    # Match common patterns in anime: [LanguageName]
    (
        r"\[(eng|english|spa|spanish|fra|french|deu|german|ita|italian|jpn|japanese)\]",
        1,
    ),
]


def normalize_language_code(code: str) -> Optional[str]:
    """
    Normalize a language code to ISO 639-2 format.

    Args:
        code: A language code or name to normalize

    Returns:
        Normalized ISO 639-2 language code, or None if code is not recognized
    """
    if not code:
        return None

    # Clean up the code
    clean_code = code.lower().strip()

    # Direct lookup in language name mapping
    if clean_code in LANGUAGE_NAME_TO_CODE:
        return LANGUAGE_NAME_TO_CODE[clean_code]

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
    if "-" in clean_code:
        base_code = clean_code.split("-")[0]
        return normalize_language_code(base_code)

    # If we get here, we can't normalize the code
    logger.debug(f"Could not normalize language code: {code}")
    return None


def detect_language_from_filename(filename: str) -> Optional[str]:
    """
    Attempt to detect language code from a filename.

    Args:
        filename: Filename to analyze

    Returns:
        Normalized language code if detected, None otherwise
    """
    if not filename:
        return None

    for pattern, group_idx in FILENAME_LANGUAGE_PATTERNS:
        match = re.search(pattern, filename.lower())
        if match:
            potential_code = match.group(group_idx)
            normalized_code = normalize_language_code(potential_code)
            if normalized_code:
                logger.debug(
                    f"Detected language '{normalized_code}' from filename '{filename}'"
                )
                return normalized_code

    return None


def is_valid_language_code(code: str) -> bool:
    """
    Check if a language code is valid.

    Args:
        code: Language code to validate

    Returns:
        True if the code is a valid ISO 639-2 code, False otherwise
    """
    if not code:
        return False

    normalized = normalize_language_code(code)
    return normalized is not None


def get_common_languages() -> List[str]:
    """
    Get a list of common language codes in ISO 639-2 format.

    Returns:
        List of common ISO 639-2 language codes
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


def enhance_language_detection(
    metadata_lang: Optional[str], filename: str, track_title: Optional[str] = None
) -> Optional[str]:
    """
    Enhance language detection by combining metadata and filename-based detection.

    Args:
        metadata_lang: Language code from metadata, if available
        filename: Filename to analyze as a fallback
        track_title: Track title to check for language information, if available

    Returns:
        Normalized language code, or None if language can't be detected
    """
    # Try metadata first
    if metadata_lang:
        normalized = normalize_language_code(metadata_lang)
        if normalized:
            return normalized

    # Try track title if available
    if track_title:
        # Look for language indicators in the track title
        # Common patterns: "English", "English 5.1", "[English]", etc.
        for pattern in [
            r"(english|spanish|french|german|italian|japanese|chinese)",
            r"(eng|spa|fra|deu|ita|jpn|zho)",
            r"\[(eng|spa|fra|deu|ita|jpn|zho)\]",
            r"\[(english|spanish|french|german|italian|japanese|chinese)\]",
        ]:
            match = re.search(pattern, track_title.lower())
            if match:
                potential_code = match.group(1)
                normalized = normalize_language_code(potential_code)
                if normalized:
                    logger.debug(
                        f"Detected language '{normalized}' from track title '{track_title}'"
                    )
                    return normalized

    # Fall back to filename analysis
    return detect_language_from_filename(filename)


def get_language_name(code: str) -> str:
    """
    Get a human-readable language name for a language code.

    Args:
        code: Language code (ISO 639-1 or ISO 639-2)

    Returns:
        Human-readable language name, or the original code if not recognized
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
