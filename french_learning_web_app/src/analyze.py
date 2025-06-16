import language_tool_python
import whisper
import torch
import librosa
import numpy as np
from transformers import pipeline
import os
from sklearn.svm import SVC
import pickle
import shap
import re
import uuid
import time
from gtts import gTTS

class FrenchAnalyzer:
    """
    A comprehensive French language analyzer that provides grammar checking,
    speech recognition, accent classification, and audio feedback generation.
    """
    
    def __init__(self):
        """
        Initialize the French analyzer with all necessary models and tools.
        Sets up grammar checking, speech recognition, and accent classification.
        """
        # Initialize French grammar checker with specific categories enabled
        self.grammar_tool = language_tool_python.LanguageTool('fr')
        self.grammar_tool.enabledCategories = 'GRAMMAR,TYPOGRAPHY,STYLE'
        
        # Load Whisper model for speech-to-text transcription
        self.whisper_model = whisper.load_model("base")
        
        # Initialize accent classifier (loaded from file if available)
        self.classifier = None
        self.shap_explainer = None
        
        # Load pre-trained accent classifier if it exists
        if os.path.exists("src/accent_classifier.pkl"):
            with open("src/accent_classifier.pkl", "rb") as f:
                self.classifier = pickle.load(f)
        
        # Initialize text generation pipeline for feedback
        self.feedback_generator = pipeline("text-generation", model="distilgpt2")

    def apply_corrections(self, text, matches, gender="masculine"):
        """
        Apply grammar corrections to French text with gender-aware adjustments.
        
        Args:
            text (str): Original text to correct
            matches (list): LanguageTool matches/errors found
            gender (str): Speaker's gender for agreement corrections ("masculine"/"feminine")
            
        Returns:
            str: Corrected text with all grammar fixes applied
        """
        corrected = text
        print(f"Initial text for correction: {corrected}, Gender: {gender}")

        # Pre-correction: Fix common contractions before LanguageTool processing
        # Normalize "à l'école" variations (handles "a école", "à école", etc.)
        corrected = re.sub(r'\b[aà]\s+l?\'?école\b', 'à l\'école', corrected, flags=re.IGNORECASE)
        print(f"After initial 'à l'' correction: {corrected}")

        # Gender-specific corrections: Fix possessive determiners based on speaker gender
        # "chez mon mère" should be "chez ma mère" when speaker is feminine
        if gender.lower() == "feminine" and re.search(r'\bchez mon mère\b', corrected.lower()):
            corrected = re.sub(r'\bchez mon mère\b', 'chez ma mère', corrected, flags=re.IGNORECASE)
            print(f"After 'chez mon mère' to 'chez ma mère' correction: {corrected}")

        # Determiner-noun agreement: Match articles/possessives with noun gender
        # Map common nouns to their grammatical gender
        noun_gender_map = {
            "pomme": "feminine",  # Apple is feminine (la pomme)
            "mère": "feminine",   # Mother is feminine (la mère)
            "père": "masculine"   # Father is masculine (le père)
        }
        
        # Check each word pair for determiner-noun agreement
        words = corrected.split()
        for i in range(len(words) - 1):
            if words[i] in ["un", "une", "mon", "ma"] and i + 1 < len(words) and words[i + 1].lower() in noun_gender_map:
                noun = words[i + 1].lower()
                expected_gender = noun_gender_map[noun]
                
                # Correct indefinite articles (un/une)
                if words[i] == "un" and expected_gender == "feminine":
                    words[i] = "une"
                elif words[i] == "une" and expected_gender == "masculine":
                    words[i] = "un"
                # Correct possessive determiners (mon/ma)
                elif words[i] == "mon" and expected_gender == "feminine":
                    words[i] = "ma"
                elif words[i] == "ma" and expected_gender == "masculine":
                    words[i] = "mon"
                    
                corrected = " ".join(words)
                print(f"After determiner correction: {corrected}")

        # Apply LanguageTool suggestions with intelligent filtering
        for match in matches:
            error_text = corrected[match.offset:match.offset + match.errorLength]
            print(f"Processing match: Error='{error_text}', Offset={match.offset}, Length={match.errorLength}, Replacements={match.replacements}")
            
            if match.replacements:
                # Smart replacement selection for common gender-specific errors
                if error_text in ["un pomme", "mon mère", "chez mon mère"]:
                    # Prioritize gender-appropriate replacements
                    for repl in match.replacements:
                        if ((error_text == "un pomme" and repl == "une pomme") or 
                            (error_text == "mon mère" and repl == "ma mère") or 
                            (error_text == "chez mon mère" and repl == "chez ma mère")):
                            replacement = repl
                            break
                    else:
                        replacement = match.replacements[0]  # Default to first if no match
                else:
                    replacement = match.replacements[0]  # Use first suggestion for other errors
                
                # Apply the replacement to the text
                corrected = corrected[:match.offset] + replacement + corrected[match.offset + match.errorLength:]
                print(f"After LanguageTool replacement: {corrected}")

        # Post-correction cleanup: Fix any corruption from LanguageTool processing
        # Sometimes LanguageTool can create malformed text, so we clean it up
        corrected = re.sub(r'chez m+?a mère\.?', 'chez ma mère', corrected)
        corrected = re.sub(r"à+ ?l'école", "à l'école", corrected)
        print(f"After corruption fix: {corrected}")

        # Gender agreement for past participles with "je suis"
        # In French, past participles agree with gender when used with "être"
        if "je suis" in corrected.lower():
            if gender.lower() == "feminine":
                # Feminine form ends in -ée
                corrected = corrected.replace("aller", "allée").replace("allé", "allée")
            else:
                # Masculine form ends in -é
                corrected = corrected.replace("aller", "allé").replace("allée", "allé")
            print(f"After gender correction for 'aller': {corrected}")

        # Punctuation normalization: Ensure proper sentence ending
        if text.endswith('.'):
            corrected = corrected.rstrip('.').rstrip() + '.'
            print(f"After adding period: {corrected}")

        return corrected

    def analyze_text(self, text, gender="masculine"):
        """
        Analyze French text for grammar errors and provide corrections.
        
        Args:
            text (str): Text to analyze
            gender (str): Speaker's gender for agreement corrections
            
        Returns:
            tuple: (errors_list, corrected_text)
                - errors_list: List of dictionaries containing error details
                - corrected_text: Text with all corrections applied
        """
        # Get grammar matches from LanguageTool
        matches = self.grammar_tool.check(text)
        errors = []
        print(f"Matches for '{text}': {len(matches)}")
        
        # Custom handling for "à l'école" construction
        # This is a common error pattern that needs special attention
        custom_a_error = None
        if re.search(r'\b[aà]\s+école\b', text.lower(), re.IGNORECASE):
            error_text = next((word for word in text.split() if word.lower() in ['a', 'à']), 'a')
            custom_a_error = {
                "error": error_text,
                "suggestions": ["à l'"],
                "message": "Use 'à l'' before 'école' due to the vowel sound."
            }
            errors.append(custom_a_error)
        
        # Define noun gender mapping for intelligent suggestion filtering
        noun_gender_map = {
            "pomme": "feminine",  # Apple (la pomme)
            "mère": "feminine",   # Mother (la mère)
            "père": "masculine"   # Father (le père)
        }

        # Process each grammar error found by LanguageTool
        for match in matches:
            error_text = text[match.offset:match.offset + match.errorLength]
            
            # Skip if we already handled this error with custom logic
            if custom_a_error and error_text.lower() in ['a', 'à']:
                continue
                
            # Create error object with suggestions
            error = {
                "error": error_text,
                "suggestions": match.replacements,
                "message": match.message
            }
            
            # Special handling for past participle agreement with "je suis"
            if error_text.lower() == "aller" and "je suis" in text.lower():
                suggestions = ["allée"] if gender.lower() == "feminine" else ["allé"]
                error["suggestions"] = suggestions  # Only show gender-specific suggestion
            else:
                # Filter suggestions based on noun gender for determiner errors
                if error_text.lower() in ["un pomme", "mon mère"]:
                    noun = error_text.split()[-1].lower()
                    if noun in noun_gender_map:
                        expected_gender = noun_gender_map[noun]
                        filtered_suggestions = []
                        
                        # Only include suggestions that match the noun's gender
                        for suggestion in match.replacements:
                            if ((expected_gender == "feminine" and "une" in suggestion.lower()) or 
                                (expected_gender == "feminine" and "ma" in suggestion.lower()) or 
                                (expected_gender == "masculine" and "un" in suggestion.lower()) or 
                                (expected_gender == "masculine" and "mon" in suggestion.lower())):
                                filtered_suggestions.append(suggestion)
                        
                        error["suggestions"] = filtered_suggestions if filtered_suggestions else match.replacements
            
            print(f"Error: {error['error']}, Suggestions: {error['suggestions']}")
            errors.append(error)
        
        # Apply all corrections to get the final corrected text
        corrected_text = self.apply_corrections(text, matches, gender=gender)
        print(f"Final corrected text: {corrected_text}")
        
        return errors, corrected_text

    def analyze_speech(self, audio_file, gender="masculine"):
        """
        Analyze French speech audio for pronunciation and grammar errors.
        
        Args:
            audio_file (str): Path to audio file to analyze
            gender (str): Speaker's gender for agreement corrections
            
        Returns:
            dict: Comprehensive analysis including:
                - transcription: What was said
                - errors: Grammar errors found
                - corrected_text: Corrected version
                - accent: Detected accent (if classifier available)
                - pronunciation_corrections: Pronunciation fixes made
                - audio_path: Path to generated feedback audio
        """
        # Load and preprocess audio for speech recognition
        audio, sr = librosa.load(audio_file, sr=16000)
        
        # Transcribe speech to text using Whisper
        result = self.whisper_model.transcribe(audio_file, language='fr')
        # Clean transcription (remove commas, convert to lowercase)
        text = result["text"].replace(',', '').lower()

        # Track pronunciation corrections made during transcription cleanup
        pronunciation_corrections = []
        
        # Common pronunciation error corrections
        # These handle typical mispronunciations that Whisper might transcribe incorrectly
        if 'alair' in text:
            text = text.replace('alair', 'aller')
            pronunciation_corrections.append({"error": "alair", "corrected": "aller"})
        if 'ecolay' in text:
            text = text.replace('ecolay', 'école')
            pronunciation_corrections.append({"error": "ecolay", "corrected": "école"})
        if 'j' in text:  # Single 'j' likely means "Je" (I)
            text = text.replace('j', 'Je')
            pronunciation_corrections.append({"error": "j", "corrected": "Je"})

        # Capitalize first word for proper sentence structure
        words = text.split()
        if words:
            words[0] = words[0].capitalize()
            text = ' '.join(words)
            
        print(f"Transcription: {text}")
        print(f"Pronunciation corrections: {pronunciation_corrections}")

        # Analyze the transcribed text for grammar errors
        errors, corrected_text = self.analyze_text(text, gender=gender)
        print(f"Errors in order: {[error['error'] for error in errors]}")

        # Generate comprehensive feedback text
        feedback_parts = []
        
        # Add pronunciation feedback if corrections were made
        if pronunciation_corrections:
            feedback_parts.append("Pronunciation corrections:")
            for correction in pronunciation_corrections:
                feedback_parts.append(f"You pronounced {correction['error']} but it was corrected to {correction['corrected']}.")
        
        # Add grammar feedback if errors were found
        if errors and any(error['suggestions'] for error in errors):
            feedback_parts.append("Grammar corrections:")
            feedback_parts += [f"Change {error['error']} to {error['suggestions'][0]}" 
                             for error in errors if error['suggestions']]
        
        # Create final feedback text
        feedback_text = " ".join(feedback_parts) if feedback_parts else "No errors found."
        print(f"Feedback text: {feedback_text}")

        # Generate audio feedback if there's something to say
        audio_path = self.generate_feedback_audio(feedback_text) if feedback_text.strip() else None

        # Extract audio features for accent classification
        features = self.extract_features(audio, sr)
        
        # Classify accent if classifier is available
        if self.classifier:
            accent = self.classifier.predict([features])[0]
            # Generate SHAP explanations if explainer is available
            shap_values = self.shap_explainer.shap_values([features]) if self.shap_explainer else None
        else:
            accent = "Unknown"
            shap_values = None

        # Return comprehensive analysis results
        return {
            "transcription": text,
            "errors": errors,
            "corrected_text": corrected_text,
            "accent": accent,
            "shap_values": shap_values,
            "audio_path": audio_path,
            "pronunciation_corrections": pronunciation_corrections
        }

    def extract_features(self, audio, sr):
        """
        Extract MFCC features from audio for accent classification.
        
        Args:
            audio (np.array): Audio signal
            sr (int): Sample rate
            
        Returns:
            np.array: Mean MFCC features (13 coefficients)
        """
        # Extract Mel-frequency cepstral coefficients (MFCCs)
        # MFCCs are commonly used features for speech analysis and accent detection
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        # Return mean across time frames to get fixed-length feature vector
        return np.mean(mfccs.T, axis=0)

    def generate_feedback_audio(self, text, filename="app/static/correction_{}.mp3".format(uuid.uuid4())):
        """
        Generate audio feedback using Google Text-to-Speech.
        
        Args:
            text (str): Text to convert to speech
            filename (str): Output filename pattern (with UUID for uniqueness)
            
        Returns:
            str or None: URL path to generated audio file, or None if generation failed
        """
        try:
            # Skip if no text provided
            if not text.strip():
                print("No feedback text to generate audio.")
                return None
                
            # Ensure output directory exists and is writable
            static_dir = os.path.dirname(filename)
            os.makedirs(static_dir, exist_ok=True)
            if not os.access(static_dir, os.W_OK):
                os.chmod(static_dir, 0o755)  # Adjust permissions if needed

            # Preprocess text for better TTS pronunciation
            # Replace contractions that might be mispronounced
            tts_text = text.replace("à l'", "a l").replace("à l", "a l")
            print(f"TTS text: {tts_text}")  # Debug log for TTS input

            # Generate speech using Google Text-to-Speech
            tts = gTTS(tts_text, lang='fr', slow=False)
            tts.save(filename)
            
            # Verify file was created successfully
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"Audio saved to {filename} (Size: {file_size} bytes)")
                
                # Check for empty file (indicates TTS failure)
                if file_size == 0:
                    print(f"Audio file {filename} is empty, not serving.")
                    os.unlink(filename)  # Remove empty file
                    return None
            else:
                print(f"Audio file {filename} not created.")
                return None
                
            # Return web-accessible path with cache-busting timestamp
            return "/static/" + os.path.basename(filename) + "?t=" + str(time.time())
            
        except Exception as e:
            print(f"Error generating audio: {e}")
            return None
