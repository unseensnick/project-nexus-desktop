"""
Language detection from filenames, titles, and metadata.

Provides intelligent language detection using pattern matching,
filename analysis, and metadata enhancement techniques.
"""

import re
from typing import List, Optional, Tuple

from core.logger import LoggerFactory
from .language_mappings import LANGUAGE_CODE_LOOKUP


class LanguageDetector:
    """
    Intelligent language detection from various sources.
    
    Uses pattern matching and heuristics to identify languages
    from filenames, metadata titles, and other text sources.
    """
    
    def __init__(self):
        """Initialize the language detector."""
        self._logger = LoggerFactory.get_logger("language_detector")
        self._filename_patterns = self._build_filename_patterns()
    
    def _build_filename_patterns(self) -> List[Tuple[str, Optional[str]]]:
        """
        Build regex patterns for detecting languages in filenames.
        
        Returns:
            List of (pattern, language_code) tuples
        """
        patterns = [
            # Bracketed language codes [lang] or (lang)
            (r'[\[\(]((?:en|eng|english))[\]\)]', "eng"),
            (r'[\[\(]((?:jp|jpn|ja|jap|japanese))[\]\)]', "jpn"),
            (r'[\[\(]((?:es|spa|spanish|español|espanol))[\]\)]', "spa"),
            (r'[\[\(]((?:fr|fra|fre|french|français|francais))[\]\)]', "fra"),
            (r'[\[\(]((?:de|deu|ger|german|deutsch))[\]\)]', "deu"),
            (r'[\[\(]((?:zh|zho|chi|cn|chinese))[\]\)]', "zho"),
            (r'[\[\(]((?:it|ita|italian|italiano))[\]\)]', "ita"),
            (r'[\[\(]((?:ko|kor|korean))[\]\)]', "kor"),
            (r'[\[\(]((?:ru|rus|russian))[\]\)]', "rus"),
            (r'[\[\(]((?:pt|por|portuguese))[\]\)]', "por"),
            
            # File extension patterns .lang.ext
            (r'\.([a-z]{2,3})\.(srt|ass|ssa|sub|idx|vtt|mks|ac3|aac|mp3|mka|mkv|mp4)$', None),
            
            # Separator patterns _lang_, .lang., -lang-
            (r'[._-]([a-z]{2,3})[._-]', None),
            
            # Full language names in separators
            (r'[._-](english|spanish|french|german|italian|japanese|korean|chinese|russian|portuguese)[._-]', None),
        ]
        
        # Compile patterns for better performance
        compiled_patterns = []
        for pattern, lang_code in patterns:
            try:
                compiled_patterns.append((re.compile(pattern, re.IGNORECASE), lang_code))
            except re.error as e:
                self._logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        return compiled_patterns
    
    def detect_from_filename(self, filename: str) -> Optional[str]:
        """
        Detect language from filename using pattern matching.
        
        Args:
            filename: The filename to analyze
            
        Returns:
            ISO 639-2 language code if detected, None otherwise
        """
        if not filename:
            return None
        
        filename = filename.lower()
        
        # Try each pattern
        for pattern, explicit_lang in self._filename_patterns:
            match = pattern.search(filename)
            if match:
                if explicit_lang:
                    # Pattern has explicit language mapping
                    return explicit_lang
                else:
                    # Extract matched group and normalize
                    matched_text = match.group(1)
                    normalized = self._normalize_detected_language(matched_text)
                    if normalized:
                        return normalized
        
        return None
    
    def detect_from_title(self, title: str) -> Optional[str]:
        """
        Detect language from track title metadata.
        
        Args:
            title: The track title to analyze
            
        Returns:
            ISO 639-2 language code if detected, None otherwise
        """
        if not title:
            return None
        
        title = title.lower().strip()
        
        # Direct lookup in language mappings
        if title in LANGUAGE_CODE_LOOKUP:
            return LANGUAGE_CODE_LOOKUP[title]
        
        # Look for language names within the title
        for variant, standard_code in LANGUAGE_CODE_LOOKUP.items():
            if variant in title:
                return standard_code
        
        return None
    
    def enhance_language_detection(
        self, 
        metadata_lang: Optional[str], 
        filename: str, 
        track_title: Optional[str] = None
    ) -> Optional[str]:
        """
        Enhance language detection using multiple sources.
        
        Combines metadata language with filename and title detection
        to provide the most accurate language identification.
        
        Args:
            metadata_lang: Language from stream metadata
            filename: Source filename
            track_title: Track title if available
            
        Returns:
            Best detected ISO 639-2 language code
        """
        # Normalize metadata language if available
        if metadata_lang:
            normalized_metadata = self._normalize_detected_language(metadata_lang)
            if normalized_metadata:
                return normalized_metadata
        
        # Try filename detection
        filename_lang = self.detect_from_filename(filename)
        if filename_lang:
            return filename_lang
        
        # Try title detection
        if track_title:
            title_lang = self.detect_from_title(track_title)
            if title_lang:
                return title_lang
        
        return None
    
    def _normalize_detected_language(self, language_text: str) -> Optional[str]:
        """
        Normalize detected language text to ISO 639-2 code.
        
        Args:
            language_text: Raw language text to normalize
            
        Returns:
            ISO 639-2 code if recognized, None otherwise
        """
        if not language_text:
            return None
        
        # Clean and normalize the text
        language_text = language_text.lower().strip()
        
        # Direct lookup in mappings
        return LANGUAGE_CODE_LOOKUP.get(language_text)
    
    def is_valid_language_code(self, code: str) -> bool:
        """
        Check if a code is a valid language identifier.
        
        Args:
            code: Language code to validate
            
        Returns:
            True if the code is recognized as a valid language identifier
        """
        if not code:
            return False
        
        return code.lower() in LANGUAGE_CODE_LOOKUP 