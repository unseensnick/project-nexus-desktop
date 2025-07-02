"""
LanguageHandler Module for language detection, normalization, and filtering.

This module handles all language-related operations including:
- Language code normalization (ISO 639-1/639-2)
- Language detection from filenames and metadata
- Language filtering and validation
- Multi-variant language support

The module provides a clean interface for working with language codes
and ensures consistent language handling across the application.
"""

from .language_handler_module import LanguageHandlerModule

__all__ = [
    "LanguageHandlerModule"
] 