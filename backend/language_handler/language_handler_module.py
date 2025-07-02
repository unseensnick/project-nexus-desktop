"""
LanguageHandler Module - Main interface for language operations.

Provides the primary interface for language detection, normalization,
and filtering operations throughout the application.
"""

from typing import Callable, List, Optional, Set, Union

from core.config_manager import ConfigManager
from core.logger import LoggerFactory
from .language_detector import LanguageDetector
from .language_mappings import (
    ALTERNATIVE_ISO_639_2,
    ISO_639_1_TO_639_2,
    ISO_639_2_TO_639_1,
    LANGUAGE_CODE_LOOKUP,
    LANGUAGE_NAMES,
    VALID_ISO_639_2_CODES,
    get_common_languages
)


class LanguageHandlerModule:
    """
    Main module for language detection, normalization, and filtering.
    
    Provides a comprehensive interface for working with language codes,
    including detection from various sources and normalization to standard formats.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the language handler module.
        
        Args:
            config_manager: Configuration manager for settings
        """
        self._config = config_manager
        self._logger = LoggerFactory.get_logger("language_handler")
        self._detector = LanguageDetector()
    
    def normalize_language_code(self, code: str) -> Optional[str]:
        """
        Convert any language identifier to standard ISO 639-2 format.
        
        Handles diverse inputs including:
        - 2-letter ISO 639-1 codes (en, fr)
        - 3-letter ISO 639-2 codes (eng, fra)
        - Alternative 3-letter codes (fre instead of fra)
        - Language names in various languages
        - Regional variants (en-us, pt-br)
        
        Args:
            code: Language identifier to normalize
            
        Returns:
            Standard 3-letter ISO 639-2 code, or None if unrecognized
        """
        if not code:
            return None
        
        # Clean input
        code = code.lower().strip()
        
        # Handle regional variants (e.g., en-us -> en)
        if '-' in code or '_' in code:
            base_code = code.split('-')[0].split('_')[0]
            code = base_code
        
        # Direct lookup in comprehensive mappings
        if code in LANGUAGE_CODE_LOOKUP:
            return LANGUAGE_CODE_LOOKUP[code]
        
        # Try ISO 639-1 to 639-2 conversion
        if code in ISO_639_1_TO_639_2:
            return ISO_639_1_TO_639_2[code]
        
        # Try alternative ISO 639-2 codes
        if code in ALTERNATIVE_ISO_639_2:
            return ALTERNATIVE_ISO_639_2[code]
        
        # Check if already valid ISO 639-2
        if code in VALID_ISO_639_2_CODES:
            return code
        
        self._logger.debug(f"Unrecognized language code: {code}")
        return None
    
    def normalize_language_codes(
        self, 
        language_codes: Union[str, List[str]], 
        remove_duplicates: bool = True
    ) -> List[str]:
        """
        Normalize a list of language codes to ISO 639-2 format.
        
        Args:
            language_codes: Single code or list of codes to normalize
            remove_duplicates: Whether to remove duplicate codes
            
        Returns:
            List of normalized ISO 639-2 codes
        """
        # Handle single string input
        if isinstance(language_codes, str):
            language_codes = [language_codes]
        
        normalized = []
        for code in language_codes:
            normalized_code = self.normalize_language_code(code)
            if normalized_code:
                normalized.append(normalized_code)
        
        # Remove duplicates if requested
        if remove_duplicates:
            normalized = list(dict.fromkeys(normalized))  # Preserves order
        
        return normalized
    
    def detect_language_from_filename(self, filename: str) -> Optional[str]:
        """
        Detect language from filename using pattern matching.
        
        Args:
            filename: Filename to analyze
            
        Returns:
            ISO 639-2 language code if detected, None otherwise
        """
        return self._detector.detect_from_filename(filename)
    
    def detect_language_from_title(self, title: str) -> Optional[str]:
        """
        Detect language from track title metadata.
        
        Args:
            title: Track title to analyze
            
        Returns:
            ISO 639-2 language code if detected, None otherwise
        """
        return self._detector.detect_from_title(title)
    
    def enhance_language_detection(
        self, 
        metadata_lang: Optional[str], 
        filename: str, 
        track_title: Optional[str] = None
    ) -> Optional[str]:
        """
        Enhance language detection using multiple sources.
        
        Args:
            metadata_lang: Language from stream metadata
            filename: Source filename
            track_title: Track title if available
            
        Returns:
            Best detected ISO 639-2 language code
        """
        return self._detector.enhance_language_detection(
            metadata_lang, filename, track_title
        )
    
    def is_valid_language_code(self, code: str) -> bool:
        """
        Check if a code is a valid language identifier.
        
        Args:
            code: Language code to validate
            
        Returns:
            True if the code is recognized
        """
        return self._detector.is_valid_language_code(code)
    
    def get_language_name(self, code: str) -> str:
        """
        Get human-readable name for a language code.
        
        Args:
            code: ISO 639-2 language code
            
        Returns:
            Human-readable language name, or the code itself if unknown
        """
        normalized_code = self.normalize_language_code(code)
        if normalized_code and normalized_code in LANGUAGE_NAMES:
            return LANGUAGE_NAMES[normalized_code]
        return code if code else "Unknown"
    
    def get_common_languages(self) -> List[str]:
        """
        Get list of commonly used language codes.
        
        Returns:
            List of ISO 639-2 codes for common languages
        """
        return get_common_languages()
    
    def create_language_filter(
        self, 
        requested_languages: List[str], 
        include_undefined: bool = False
    ) -> Callable[[Optional[str]], bool]:
        """
        Create a filter function for language-based filtering.
        
        Args:
            requested_languages: List of language codes to accept
            include_undefined: Whether to include tracks with no language
            
        Returns:
            Filter function that accepts language codes
        """
        # Normalize requested languages
        normalized_languages = set(self.normalize_language_codes(requested_languages))
        
        def language_filter(language_code: Optional[str]) -> bool:
            """Filter function for language matching."""
            if language_code is None:
                return include_undefined
            
            normalized = self.normalize_language_code(language_code)
            return normalized in normalized_languages
        
        return language_filter
    
    def filter_by_languages(
        self, 
        items: List[dict], 
        requested_languages: List[str], 
        language_key: str = "language",
        include_undefined: bool = False
    ) -> List[dict]:
        """
        Filter a list of items by language criteria.
        
        Args:
            items: List of dictionaries to filter
            requested_languages: List of language codes to accept
            language_key: Key in dictionaries containing language code
            include_undefined: Whether to include items with no language
            
        Returns:
            Filtered list of items matching language criteria
        """
        language_filter = self.create_language_filter(
            requested_languages, include_undefined
        )
        
        filtered_items = []
        for item in items:
            language_code = item.get(language_key)
            if language_filter(language_code):
                filtered_items.append(item)
        
        return filtered_items
    
    def get_available_languages_from_items(
        self, 
        items: List[dict], 
        language_key: str = "language"
    ) -> Set[str]:
        """
        Extract all available languages from a list of items.
        
        Args:
            items: List of dictionaries containing language information
            language_key: Key in dictionaries containing language code
            
        Returns:
            Set of normalized language codes found in the items
        """
        languages = set()
        for item in items:
            language_code = item.get(language_key)
            if language_code:
                normalized = self.normalize_language_code(language_code)
                if normalized:
                    languages.add(normalized)
        
        return languages
    
    def normalize_language_list(self, languages: List[str]) -> List[str]:
        """
        Normalize a list of language codes to ISO 639-1 format.
        
        Args:
            languages: List of language codes to normalize
            
        Returns:
            List of normalized language codes
        """
        normalized = []
        for lang in languages:
            normalized_lang = self.normalize_language_code(lang)
            if normalized_lang and normalized_lang not in normalized:
                normalized.append(normalized_lang)
        
        return normalized
    
    def is_language_match(self, track_language: Optional[str], target_languages: List[str]) -> bool:
        """
        Check if a track language matches any of the target languages.
        
        Args:
            track_language: Language code from the track (may be None)
            target_languages: List of target language codes to match against
            
        Returns:
            True if track language matches any target language, False otherwise
        """
        if not track_language:
            return False
        
        # Normalize the track language
        normalized_track_lang = self.normalize_language_code(track_language)
        if not normalized_track_lang:
            return False
        
        # Normalize target languages
        normalized_targets = self.normalize_language_list(target_languages)
        
        # Check for match
        return normalized_track_lang in normalized_targets 