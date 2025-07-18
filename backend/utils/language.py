"""
Language Utilities Module for Project Nexus Desktop.

This module provides robust language identification, normalization, and validation
for media tracks using the new centralized configuration system. It implements
confidence-based detection with progressive fallback strategies.

Key features:
- All language data sourced from language-mappings.json configuration
- Confidence-based detection with 0.0-1.0 scoring
- Progressive fallback trying best methods first
- Edge case mapping for common variants
- Context-aware detection using file patterns
- Backward compatibility with existing code
- Minimal hardcoded fallback only when JSON loading fails

All functions use ISO 639-2 (3-letter codes) as the standardized format,
with comprehensive configuration-driven mapping for maximum flexibility.
Data hierarchy: language-mappings.json → minimal fallback → error handling
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass

from core.config import get_language_mappings

logger = logging.getLogger(__name__)

@dataclass
class LanguageDetectionResult:
    """Result of language detection with confidence information."""
    language_code: str
    confidence: float
    detection_method: str
    source_value: Optional[str] = None
    
    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

class LanguageDetector:
    """
    Centralized language detection system with confidence-based scoring.
    
    This class loads language mappings from configuration files and provides
    confidence-based detection methods with progressive fallback strategies.
    """
    
    def __init__(self):
        self._config = None
        self._iso_639_1_to_639_2 = {}
        self._iso_639_2_to_639_1 = {}
        self._language_name_mappings = {}
        self._regional_variants = {}
        self._filename_patterns = []
        self._fallback_config = {}
        self._reverse_lookup = {}
        
        # Load configuration on first use
        self._load_config()
    
    def _load_config(self):
        """Load language configuration from JSON files."""
        try:
            self._config = get_language_mappings()
            
            # Load ISO code mappings
            self._iso_639_1_to_639_2 = self._config.get("iso_639_1_to_639_2", {})
            self._iso_639_2_to_639_1 = {v: k for k, v in self._iso_639_1_to_639_2.items()}
            
            # Load language name mappings
            self._language_name_mappings = self._config.get("language_name_mappings", {})
            
            # Load regional variants
            self._regional_variants = self._config.get("regional_variants", {})
            
            # Load filename patterns
            filename_config = self._config.get("filename_patterns", {})
            self._filename_patterns = filename_config.get("patterns", [])
            
            # Load fallback configuration
            self._fallback_config = self._config.get("fallback_detection", {})
            
            # Create reverse lookup table
            self._build_reverse_lookup()
            
            logger.info("Language detection configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load language configuration: {e}")
            # Use minimal fallback configuration
            self._use_fallback_config()
    
    def _use_fallback_config(self):
        """Use minimal fallback configuration if JSON loading fails."""
        logger.warning("Using minimal fallback language configuration - functionality will be limited")
        
        # Only the most essential mappings for basic functionality
        self._iso_639_1_to_639_2 = {
            "en": "eng", "es": "spa", "fr": "fra", "de": "deu", "it": "ita",
            "ja": "jpn", "ko": "kor", "zh": "zho", "ru": "rus", "pt": "por"
        }
        self._iso_639_2_to_639_1 = {v: k for k, v in self._iso_639_1_to_639_2.items()}
        
        # Only the most common language names
        self._language_name_mappings = {
            "english": "eng", "spanish": "spa", "french": "fra", "german": "deu",
            "italian": "ita", "japanese": "jpn", "korean": "kor", "chinese": "zho",
            "russian": "rus", "portuguese": "por", "unknown": "und"
        }
        
        # Only the most common regional variants
        self._regional_variants = {
            "en-US": "eng", "en-GB": "eng", "es-ES": "spa", "fr-FR": "fra",
            "de-DE": "deu", "it-IT": "ita", "pt-PT": "por", "pt-BR": "por"
        }
        
        # Only basic filename patterns
        self._filename_patterns = [
            {"pattern": "\\.(eng|english)\\.", "language": "eng", "confidence": 0.9},
            {"pattern": "\\.(spa|spanish)\\.", "language": "spa", "confidence": 0.9},
            {"pattern": "\\.(fra|french)\\.", "language": "fra", "confidence": 0.9}
        ]
        
        self._fallback_config = {
            "confidence_threshold": 0.6,
            "use_filename_analysis": True,
            "use_title_analysis": True,
            "default_language": "eng",
            "common_undetermined": ["und", "unknown", "n/a", "null", ""]
        }
        
        # Create minimal config structure for consistency
        self._config = {
            "filename_patterns": {
                "confidence_high": 0.9,
                "confidence_medium": 0.7,
                "confidence_low": 0.5,
                "patterns": self._filename_patterns
            },
            "alternative_iso_codes": {
                "fre": "fra",  # French (bibliographic)
                "ger": "deu",  # German (bibliographic)
                "dut": "nld",  # Dutch (bibliographic)
                "chi": "zho",  # Chinese (bibliographic)
                "cze": "ces",  # Czech (bibliographic)
                "rum": "ron",  # Romanian (bibliographic)
                "slo": "slk",  # Slovak (bibliographic)
                "per": "fas"   # Persian (bibliographic)
            }
        }
        
        self._build_reverse_lookup()
    
    def _build_reverse_lookup(self):
        """Build comprehensive reverse lookup table for all language variants."""
        self._reverse_lookup = {}
        
        # Add ISO 639-1 codes
        for iso1, iso2 in self._iso_639_1_to_639_2.items():
            self._reverse_lookup[iso1.lower()] = iso2
        
        # Add ISO 639-2 codes (identity mapping)
        for iso2 in self._iso_639_1_to_639_2.values():
            self._reverse_lookup[iso2.lower()] = iso2
        
        # Add language names from configuration
        for name, iso2 in self._language_name_mappings.items():
            self._reverse_lookup[name.lower()] = iso2
        
        # Add regional variants from configuration
        for variant, iso2 in self._regional_variants.items():
            self._reverse_lookup[variant.lower()] = iso2
            # Also add without hyphens/underscores (e.g., "enus" for "en-US")
            clean_variant = variant.lower().replace("-", "").replace("_", "")
            if clean_variant != variant.lower():
                self._reverse_lookup[clean_variant] = iso2
        
        # Add alternative ISO codes from configuration
        alternative_codes = self._config.get("alternative_iso_codes", {})
        for alt_code, standard_code in alternative_codes.items():
            self._reverse_lookup[alt_code.lower()] = standard_code
    
    def normalize_language_code(self, code: str) -> Optional[str]:
        """
        Convert any language identifier to standard ISO 639-2 format.
        
        Args:
            code: Language identifier to normalize
            
        Returns:
            Standard 3-letter ISO 639-2 code, or None if unrecognized
        """
        if not code:
            return None
        
        # Clean up the code
        clean_code = code.lower().strip()
        
        # Handle common undetermined values
        if clean_code in self._fallback_config.get("common_undetermined", []):
            return "und"
        
        # Direct lookup in reverse mapping
        if clean_code in self._reverse_lookup:
            return self._reverse_lookup[clean_code]
        
        # Handle country code suffixes (e.g., en-us, pt-br)
        if "-" in clean_code or "_" in clean_code:
            base_code = re.split(r'[-_]', clean_code)[0]
            return self.normalize_language_code(base_code)
        
        # Log unrecognized codes for debugging
        logger.debug(f"Could not normalize language code: {code}")
        return None
    
    def detect_from_metadata(self, metadata_code: str) -> LanguageDetectionResult:
        """
        Detect language from file metadata with confidence scoring.
        
        Args:
            metadata_code: Language code from file metadata
            
        Returns:
            LanguageDetectionResult with confidence score
        """
        if not metadata_code:
            return LanguageDetectionResult(
                language_code="und",
                confidence=0.0,
                detection_method="metadata",
                source_value=metadata_code
            )
        
        normalized = self.normalize_language_code(metadata_code)
        if normalized:
            # High confidence for normalized metadata
            confidence = 0.9 if normalized != "und" else 0.1
            return LanguageDetectionResult(
                language_code=normalized,
                confidence=confidence,
                detection_method="metadata",
                source_value=metadata_code
            )
        
        # Low confidence for unrecognized metadata
        return LanguageDetectionResult(
            language_code="und",
            confidence=0.2,
            detection_method="metadata",
            source_value=metadata_code
        )
    
    def detect_from_filename(self, filename: str) -> LanguageDetectionResult:
        """
        Detect language from filename using pattern matching with configuration-based confidence.
        
        Args:
            filename: Filename to analyze
            
        Returns:
            LanguageDetectionResult with confidence score
        """
        if not filename:
            return LanguageDetectionResult(
                language_code="und",
                confidence=0.0,
                detection_method="filename",
                source_value=filename
            )
        
        filename_lower = filename.lower()
        
        # Get confidence thresholds from configuration
        filename_config = self._config.get("filename_patterns", {})
        confidence_high = filename_config.get("confidence_high", 0.9)
        confidence_medium = filename_config.get("confidence_medium", 0.7)
        confidence_low = filename_config.get("confidence_low", 0.5)
        
        # Try configured patterns (highest priority)
        for pattern_config in self._filename_patterns:
            pattern = pattern_config.get("pattern", "")
            expected_lang = pattern_config.get("language", "")
            confidence = pattern_config.get("confidence", confidence_medium)
            
            if pattern and expected_lang:
                try:
                    if re.search(pattern, filename_lower):
                        return LanguageDetectionResult(
                            language_code=expected_lang,
                            confidence=confidence,
                            detection_method="filename_pattern_config",
                            source_value=filename
                        )
                except re.error:
                    logger.warning(f"Invalid regex pattern in config: {pattern}")
        
        # Try generic patterns with configuration-based confidence levels
        generic_patterns = [
            # Match .lang. format before file extension (high confidence)
            (r'\.([a-z]{2,3})\.(srt|ass|ssa|sub|idx|vtt|mks|ac3|aac|mp3|mka|mkv|mp4)$', confidence_high),
            # Match [lang] or (lang) formats (medium confidence)
            (r'[\[\(]([a-z]{2,3})[\]\)]', confidence_medium),
            # Match _lang_, -lang- formats (medium confidence)
            (r'[._-]([a-z]{2,3})[._-]', confidence_medium),
            # Match lang at end of filename (lower confidence)
            (r'[._-]([a-z]{2,3})$', confidence_low),
            # Match lang at beginning of filename (lower confidence)
            (r'^([a-z]{2,3})[._-]', confidence_low),
        ]
        
        for pattern, confidence in generic_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                potential_code = match.group(1)
                normalized = self.normalize_language_code(potential_code)
                if normalized and normalized != "und":
                    return LanguageDetectionResult(
                        language_code=normalized,
                        confidence=confidence,
                        detection_method="filename_generic",
                        source_value=filename
                    )
        
        # No pattern matched
        return LanguageDetectionResult(
            language_code="und",
            confidence=0.0,
            detection_method="filename",
            source_value=filename
        )
    
    def detect_from_title(self, title: str) -> LanguageDetectionResult:
        """
        Detect language from track title.
        
        Args:
            title: Track title to analyze
            
        Returns:
            LanguageDetectionResult with confidence score
        """
        if not title:
            return LanguageDetectionResult(
                language_code="und",
                confidence=0.0,
                detection_method="title",
                source_value=title
            )
        
        title_lower = title.lower()
        
        # Try language names
        for name, iso2 in self._language_name_mappings.items():
            if name.lower() in title_lower:
                return LanguageDetectionResult(
                    language_code=iso2,
                    confidence=0.8,
                    detection_method="title_name",
                    source_value=title
                )
        
        # Try language codes in brackets
        bracket_patterns = [
            (r'\[([a-z]{2,3})\]', 0.7),
            (r'\(([a-z]{2,3})\)', 0.6),
        ]
        
        for pattern, confidence in bracket_patterns:
            match = re.search(pattern, title_lower)
            if match:
                potential_code = match.group(1)
                normalized = self.normalize_language_code(potential_code)
                if normalized:
                    return LanguageDetectionResult(
                        language_code=normalized,
                        confidence=confidence,
                        detection_method="title_bracket",
                        source_value=title
                    )
        
        # No pattern matched
        return LanguageDetectionResult(
            language_code="und",
            confidence=0.0,
            detection_method="title",
            source_value=title
        )
    
    def detect_with_confidence(
        self,
        metadata_lang: Optional[str] = None,
        filename: Optional[str] = None,
        track_title: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> LanguageDetectionResult:
        """
        Detect language using multiple methods with confidence-based selection.
        
        Uses fallback configuration flags to determine which detection methods to use.
        
        Args:
            metadata_lang: Language from file metadata
            filename: Filename for pattern analysis
            track_title: Track title for analysis
            context: Additional context for detection
            
        Returns:
            LanguageDetectionResult with best confidence score
        """
        candidates = []
        
        # Try metadata detection (always enabled as it's most reliable)
        if metadata_lang:
            result = self.detect_from_metadata(metadata_lang)
            candidates.append(result)
        
        # Try title detection (check configuration flag)
        use_title_analysis = self._fallback_config.get("use_title_analysis", True)
        if track_title and use_title_analysis:
            result = self.detect_from_title(track_title)
            candidates.append(result)
        
        # Try filename detection (check configuration flag)
        use_filename_analysis = self._fallback_config.get("use_filename_analysis", True)
        if filename and use_filename_analysis:
            result = self.detect_from_filename(filename)
            candidates.append(result)
        
        # Select best candidate based on confidence
        if candidates:
            best_candidate = max(candidates, key=lambda x: x.confidence)
            
            # Check if confidence meets threshold
            threshold = self._fallback_config.get("confidence_threshold", 0.6)
            if best_candidate.confidence >= threshold:
                return best_candidate
        
        # Fall back to default language
        default_lang = self._fallback_config.get("default_language", "eng")
        return LanguageDetectionResult(
            language_code=default_lang,
            confidence=0.1,
            detection_method="fallback",
            source_value=None
        )
    
    def is_valid_language_code(self, code: str) -> bool:
        """
        Check if a language code is valid and can be normalized.
        
        Args:
            code: Language code to validate
            
        Returns:
            True if code is valid
        """
        return self.normalize_language_code(code) is not None
    
    def get_language_name(self, code: str) -> str:
        """
        Get human-readable language name from code using configuration data.
        
        Args:
            code: Language code
            
        Returns:
            Human-readable language name
        """
        normalized = self.normalize_language_code(code)
        if not normalized:
            return code
        
        # Create reverse mapping from ISO codes to language names
        # This uses the configuration data exclusively
        iso_to_name = {}
        for name, iso2 in self._language_name_mappings.items():
            if iso2 not in iso_to_name:
                # Use the first (typically most common) name for each ISO code
                iso_to_name[iso2] = name.title()
        
        # Use configuration name first, then title case of code as final fallback
        return iso_to_name.get(normalized) or normalized.title()
    
    def get_supported_languages(self) -> List[str]:
        """
        Get list of all supported language codes from configuration.
        
        Returns:
            List of ISO 639-2 language codes
        """
        # Collect all unique ISO 639-2 codes from various sources
        languages = set()
        
        # From ISO 639-1 mappings
        languages.update(self._iso_639_1_to_639_2.values())
        
        # From language name mappings
        languages.update(self._language_name_mappings.values())
        
        # From regional variants
        languages.update(self._regional_variants.values())
        
        # From filename patterns
        for pattern in self._filename_patterns:
            lang = pattern.get("language")
            if lang:
                languages.add(lang)
        
        return sorted(list(languages))
    
    def get_configuration_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the loaded configuration.
        
        Returns:
            Dictionary with configuration statistics
        """
        alternative_codes = self._config.get("alternative_iso_codes", {})
        
        return {
            "configuration_source": "language-mappings.json" if len(self._iso_639_1_to_639_2) > 10 else "minimal fallback",
            "iso_639_1_codes": len(self._iso_639_1_to_639_2),
            "language_names": len(self._language_name_mappings),
            "regional_variants": len(self._regional_variants),
            "alternative_codes": len(alternative_codes),
            "filename_patterns": len(self._filename_patterns),
            "reverse_lookup_entries": len(self._reverse_lookup),
            "supported_languages": len(self.get_supported_languages()),
            "confidence_threshold": self._fallback_config.get("confidence_threshold", 0.6),
            "default_language": self._fallback_config.get("default_language", "eng"),
            "filename_analysis_enabled": self._fallback_config.get("use_filename_analysis", True),
            "title_analysis_enabled": self._fallback_config.get("use_title_analysis", True)
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the loaded configuration for consistency.
        
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Check ISO code mappings
        for iso1, iso2 in self._iso_639_1_to_639_2.items():
            if len(iso1) != 2:
                issues.append(f"Invalid ISO 639-1 code length: {iso1}")
            if len(iso2) != 3:
                issues.append(f"Invalid ISO 639-2 code length: {iso2}")
        
        # Check language name mappings
        for name, iso2 in self._language_name_mappings.items():
            if len(iso2) != 3:
                issues.append(f"Invalid ISO 639-2 code in language mapping: {name} -> {iso2}")
            if not name.isalpha():
                warnings.append(f"Non-alphabetic language name: {name}")
        
        # Check filename patterns
        for i, pattern in enumerate(self._filename_patterns):
            if "pattern" not in pattern:
                issues.append(f"Filename pattern {i} missing 'pattern' field")
            if "language" not in pattern:
                issues.append(f"Filename pattern {i} missing 'language' field")
            if "confidence" in pattern:
                conf = pattern["confidence"]
                if not 0.0 <= conf <= 1.0:
                    issues.append(f"Invalid confidence value {conf} in pattern {i}")
        
        # Check alternative ISO codes
        alternative_codes = self._config.get("alternative_iso_codes", {})
        for alt_code, standard_code in alternative_codes.items():
            if len(alt_code) != 3:
                issues.append(f"Invalid alternative code length: {alt_code}")
            if len(standard_code) != 3:
                issues.append(f"Invalid standard code length in alternative mapping: {alt_code} -> {standard_code}")
            if alt_code == standard_code:
                warnings.append(f"Alternative code maps to itself: {alt_code} -> {standard_code}")
        
        # Check reverse lookup consistency
        expected_entries = (
            len(self._iso_639_1_to_639_2) +  # ISO 639-1 codes
            len(self._iso_639_1_to_639_2) +  # ISO 639-2 codes (identity)
            len(self._language_name_mappings) +  # Language names
            len(self._regional_variants) +  # Regional variants
            len(self._regional_variants) +  # Clean variants (without hyphens)
            len(alternative_codes)  # Alternative codes
        )
        
        if len(self._reverse_lookup) < expected_entries * 0.8:  # Allow some overlap
            warnings.append("Reverse lookup table may be incomplete")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_issues": len(issues),
            "total_warnings": len(warnings)
        }

# Global detector instance
_detector = None

def get_detector() -> LanguageDetector:
    """Get the global language detector instance."""
    global _detector
    if _detector is None:
        _detector = LanguageDetector()
    return _detector

# Backward compatibility functions
def normalize_language_code(code: str) -> Optional[str]:
    """Normalize language code to ISO 639-2 format."""
    return get_detector().normalize_language_code(code)

def detect_language_from_filename(filename: str) -> Optional[str]:
    """Detect language from filename (backward compatibility)."""
    result = get_detector().detect_from_filename(filename)
    return result.language_code if result.confidence > 0.5 else None

def detect_language_from_title(title: str) -> Optional[str]:
    """Detect language from title (backward compatibility)."""
    result = get_detector().detect_from_title(title)
    return result.language_code if result.confidence > 0.5 else None

def enhance_language_detection(
    metadata_lang: Optional[str],
    filename: str,
    track_title: Optional[str] = None
) -> Optional[str]:
    """Enhanced language detection with fallback (backward compatibility)."""
    result = get_detector().detect_with_confidence(
        metadata_lang=metadata_lang,
        filename=filename,
        track_title=track_title
    )
    return result.language_code

def is_valid_language_code(code: str) -> bool:
    """Check if language code is valid (backward compatibility)."""
    return get_detector().is_valid_language_code(code)

def get_language_name(code: str) -> str:
    """Get language name from code (backward compatibility)."""
    return get_detector().get_language_name(code)

def get_common_languages() -> List[str]:
    """Get list of common language codes from configuration."""
    detector = get_detector()
    # Get languages from ISO 639-1 mappings as they represent the most common ones
    common_languages = list(detector._iso_639_1_to_639_2.values())
    return sorted(common_languages)

def normalize_language_codes(
    language_codes: Union[str, List[str]],
    remove_duplicates: bool = True
) -> List[str]:
    """Normalize multiple language codes."""
    if isinstance(language_codes, str):
        codes_list = [language_codes]
    else:
        codes_list = language_codes
    
    detector = get_detector()
    normalized_codes = []
    
    for code in codes_list:
        if not code:
            continue
        
        norm_code = detector.normalize_language_code(code)
        if norm_code:
            normalized_codes.append(norm_code)
        else:
            logger.warning(f"Could not normalize language code: {code}")
            normalized_codes.append(code.lower())
    
    if remove_duplicates:
        return list(dict.fromkeys(normalized_codes))
    
    return normalized_codes

def filter_by_languages(
    all_items: List[Dict],
    requested_languages: List[str],
    lang_key: str = "language",
    include_undefined: bool = False
) -> List[Dict]:
    """Filter items by language criteria."""
    if not all_items or not requested_languages:
        return all_items
    
    norm_requested = normalize_language_codes(requested_languages)
    if include_undefined:
        norm_requested.append("und")
    
    filtered_items = []
    for item in all_items:
        item_lang = item.get(lang_key)
        if not item_lang:
            if include_undefined:
                filtered_items.append(item)
            continue
        
        norm_item_lang = normalize_language_code(item_lang) or item_lang.lower()
        if norm_item_lang in norm_requested:
            filtered_items.append(item)
    
    return filtered_items

def create_language_filter(
    requested_languages: List[str],
    include_undefined: bool = False
) -> callable:
    """Create a reusable language filter function."""
    norm_requested = normalize_language_codes(requested_languages)
    if include_undefined:
        norm_requested.append("und")
    
    def language_filter(language_code: Optional[str]) -> bool:
        """Test if language code matches filter criteria."""
        if not language_code or language_code.lower() in ("und", "unknown", ""):
            return include_undefined
        
        norm_lang = normalize_language_code(language_code) or language_code.lower()
        return norm_lang in norm_requested
    
    return language_filter

# Enhanced functionality (new in redesigned system)
def detect_language_with_confidence(
    metadata_lang: Optional[str] = None,
    filename: Optional[str] = None,
    track_title: Optional[str] = None,
    context: Optional[Dict] = None
) -> LanguageDetectionResult:
    """
    Detect language with confidence scoring and detailed results.
    
    Args:
        metadata_lang: Language from file metadata
        filename: Filename for pattern analysis
        track_title: Track title for analysis
        context: Additional context for detection
        
    Returns:
        LanguageDetectionResult with confidence and method information
    """
    return get_detector().detect_with_confidence(
        metadata_lang=metadata_lang,
        filename=filename,
        track_title=track_title,
        context=context
    )

def get_supported_languages() -> List[str]:
    """Get list of all supported language codes from configuration."""
    return get_detector().get_supported_languages()

def get_language_configuration_stats() -> Dict[str, Any]:
    """Get statistics about the loaded language configuration."""
    return get_detector().get_configuration_stats()

def validate_language_configuration() -> Dict[str, Any]:
    """Validate the loaded language configuration for consistency."""
    return get_detector().validate_configuration()

def reload_language_configuration() -> None:
    """Reload language configuration from files."""
    global _detector
    _detector = None  # Force reload on next access
    logger.info("Language configuration will be reloaded on next access") 