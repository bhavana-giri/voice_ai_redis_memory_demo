"""Multi-language support leveraging Sarvam AI's language capabilities."""
import os
from typing import Optional, Dict, List
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()


class LanguageSupport:
    """Multi-language support for voice journal using Sarvam AI."""
    
    # Sarvam AI supported languages (22 Indian languages + English)
    SUPPORTED_LANGUAGES = {
        "en-IN": "English (India)",
        "hi-IN": "Hindi",
        "bn-IN": "Bengali",
        "gu-IN": "Gujarati",
        "kn-IN": "Kannada",
        "ml-IN": "Malayalam",
        "mr-IN": "Marathi",
        "od-IN": "Odia",
        "pa-IN": "Punjabi",
        "ta-IN": "Tamil",
        "te-IN": "Telugu",
        "ur-IN": "Urdu",
        "as-IN": "Assamese",
        "bho-IN": "Bhojpuri",
        "doi-IN": "Dogri",
        "gom-IN": "Konkani",
        "ks-IN": "Kashmiri",
        "mai-IN": "Maithili",
        "mni-IN": "Manipuri",
        "ne-IN": "Nepali",
        "sa-IN": "Sanskrit",
        "sd-IN": "Sindhi",
        "sat-IN": "Santali"
    }
    
    # TTS speaker voices available
    TTS_SPEAKERS = [
        "shubh", "jaya", "neha", "anuj", "priya", "vivek"
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        self.client = SarvamAI(api_subscription_key=self.api_key)
    
    def get_language_name(self, code: str) -> str:
        """Get human-readable language name from code."""
        return self.SUPPORTED_LANGUAGES.get(code, f"Unknown ({code})")
    
    def is_supported(self, language_code: str) -> bool:
        """Check if a language is supported."""
        return language_code in self.SUPPORTED_LANGUAGES
    
    def list_languages(self) -> Dict[str, str]:
        """List all supported languages."""
        return self.SUPPORTED_LANGUAGES.copy()
    
    def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> str:
        """
        Translate text between languages using Sarvam AI.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            Translated text
        """
        response = self.client.translate.translate(
            input=text,
            source_language_code=source_language,
            target_language_code=target_language
        )
        return response.translated_text
    
    def transliterate(
        self,
        text: str,
        source_language: str,
        target_language: str = "en-IN"
    ) -> str:
        """
        Transliterate text to another script.
        
        Args:
            text: Text to transliterate
            source_language: Source language code
            target_language: Target language code (default: English)
            
        Returns:
            Transliterated text
        """
        response = self.client.transliterate.transliterate(
            input=text,
            source_language_code=source_language,
            target_language_code=target_language
        )
        return response.transliterated_text
    
    def detect_language_from_transcript(self, transcript: str) -> str:
        """
        Detect language from text content.
        Note: This is a simplified heuristic. Sarvam STT auto-detects during transcription.
        """
        # Common Hindi characters
        hindi_chars = set("अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह")
        
        # Check for Hindi
        if any(c in hindi_chars for c in transcript):
            return "hi-IN"
        
        # Default to English
        return "en-IN"
    
    def get_speaker_for_language(self, language_code: str) -> str:
        """Get recommended TTS speaker for a language."""
        # Map languages to appropriate speakers
        speaker_map = {
            "hi-IN": "shubh",
            "en-IN": "shubh",
            "bn-IN": "jaya",
            "ta-IN": "priya",
            "te-IN": "neha",
            "mr-IN": "anuj",
            "gu-IN": "vivek"
        }
        return speaker_map.get(language_code, "shubh")
    
    def format_multilingual_entry(
        self,
        transcript: str,
        language_code: str,
        include_translation: bool = False,
        target_language: str = "en-IN"
    ) -> Dict[str, str]:
        """
        Format entry with optional translation.
        
        Args:
            transcript: Original transcript
            language_code: Original language code
            include_translation: Whether to include English translation
            target_language: Target language for translation
            
        Returns:
            Dict with original and optionally translated text
        """
        result = {
            "original": transcript,
            "language": language_code,
            "language_name": self.get_language_name(language_code)
        }
        
        if include_translation and language_code != target_language:
            try:
                result["translation"] = self.translate_text(
                    transcript, language_code, target_language
                )
                result["translation_language"] = target_language
            except Exception:
                result["translation"] = None
        
        return result

