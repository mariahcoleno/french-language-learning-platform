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
    def __init__(self):
        self.grammar_tool = language_tool_python.LanguageTool('fr')
        self.grammar_tool.enabledCategories = 'GRAMMAR,TYPOGRAPHY,STYLE'
        self.whisper_model = whisper.load_model("base")
        self.classifier = None
        self.shap_explainer = None
        if os.path.exists("src/accent_classifier.pkl"):
            with open("src/accent_classifier.pkl", "rb") as f:
                self.classifier = pickle.load(f)
        self.feedback_generator = pipeline("text-generation", model="distilgpt2")

    def apply_corrections(self, text, matches, gender="masculine"):
            corrected = text
            print(f"Initial text for correction: {corrected}, Gender: {gender}")

            # Preprocess to normalize "à l’école" before LanguageTool with stricter matching
            corrected = re.sub(r'\b[aà]\s+l?’?école\b', 'à l’école', corrected, flags=re.IGNORECASE)
            print(f"After initial 'à l’' correction: {corrected}")

            # Handle "mon mère" → "ma mère" for feminine before LanguageTool with context
            if gender.lower() == "feminine" and re.search(r'\bchez mon mère\b', corrected.lower()):
                corrected = re.sub(r'\bchez mon mère\b', 'chez ma mère', corrected, flags=re.IGNORECASE)
                print(f"After 'chez mon mère' to 'chez ma mère' correction: {corrected}")

            # Handle determiner-noun agreement based on noun gender before LanguageTool
            noun_gender_map = {
                "pomme": "feminine",  # Apple is feminine
                "mère": "feminine",   # Mother is feminine
                "père": "masculine"   # Father is masculine
            }
            words = corrected.split()
            for i in range(len(words) - 1):
                if words[i] in ["un", "une", "mon", "ma"] and i + 1 < len(words) and words[i + 1].lower() in noun_gender_map:
                    noun = words[i + 1].lower()
                    expected_gender = noun_gender_map[noun]
                    if words[i] == "un" and expected_gender == "feminine":
                        words[i] = "une"
                    elif words[i] == "une" and expected_gender == "masculine":
                        words[i] = "un"
                    elif words[i] == "mon" and expected_gender == "feminine":
                        words[i] = "ma"
                    elif words[i] == "ma" and expected_gender == "masculine":
                        words[i] = "mon"
                    corrected = " ".join(words)
                    print(f"After determiner correction: {corrected}")

            # Apply LanguageTool replacements with filtered suggestions
            for match in matches:
                error_text = corrected[match.offset:match.offset + match.errorLength]
                print(f"Processing match: Error='{error_text}', Offset={match.offset}, Length={match.errorLength}, Replacements={match.replacements}")
                if match.replacements:
                    # Filter replacements to prioritize correct gender for determiners
                    if error_text in ["un pomme", "mon mère", "chez mon mère"]:
                        for repl in match.replacements:
                            if (error_text == "un pomme" and repl == "une pomme") or (error_text == "mon mère" and repl == "ma mère") or (error_text == "chez mon mère" and repl == "chez ma mère"):
                                replacement = repl
                                break
                        else:
                            replacement = match.replacements[0]  # Default to first if no match
                    else:
                        replacement = match.replacements[0]
                    corrected = corrected[:match.offset] + replacement + corrected[match.offset + match.errorLength:]
                    print(f"After LanguageTool replacement: {corrected}")

            # Fallback to fix corruption from LanguageTool
            corrected = re.sub(r'chez m+?a mère\.?', 'chez ma mère', corrected)
            corrected = re.sub(r'à+ ?l’école', 'à l’école', corrected)
            print(f"After corruption fix: {corrected}")

            # Apply gender correction last
            if "je suis" in corrected.lower():
                if gender.lower() == "feminine":
                    corrected = corrected.replace("aller", "allée").replace("allé", "allée")
                else:
                    corrected = corrected.replace("aller", "allé").replace("allée", "allé")
                print(f"After gender correction for 'aller': {corrected}")

            # Ensure corrected text ends with exactly one period if input had one
            if text.endswith('.'):
                corrected = corrected.rstrip('.').rstrip() + '.'
                print(f"After adding period: {corrected}")

            return corrected

    def analyze_text(self, text, gender="masculine"):
        matches = self.grammar_tool.check(text)
        errors = []
        print(f"Matches for '{text}': {len(matches)}")
        custom_a_error = None
        if re.search(r'\b[aà]\s+école\b', text.lower(), re.IGNORECASE):
            error_text = next((word for word in text.split() if word.lower() in ['a', 'à']), 'a')
            custom_a_error = {
                "error": error_text,
                "suggestions": ["à l’"],
                "message": "Use 'à l’' before 'école' due to the vowel sound."
            }
            errors.append(custom_a_error)
        
        # Define noun gender map for filtering suggestions
        noun_gender_map = {
            "pomme": "feminine",
            "mère": "feminine",
            "père": "masculine"
        }

        for match in matches:
            error_text = text[match.offset:match.offset + match.errorLength]
            if custom_a_error and error_text.lower() in ['a', 'à']:
                continue
            error = {
                "error": error_text,
                "suggestions": match.replacements,
                "message": match.message
            }
            if error_text.lower() == "aller" and "je suis" in text.lower():
                suggestions = ["allée"] if gender.lower() == "feminine" else ["allé"]
                error["suggestions"] = suggestions  # Only show gender-specific suggestion
            else:
                # Filter suggestions based on noun gender
                if error_text.lower() in ["un pomme", "mon mère"]:
                    noun = error_text.split()[-1].lower()
                    if noun in noun_gender_map:
                        expected_gender = noun_gender_map[noun]
                        filtered_suggestions = []
                        for suggestion in match.replacements:
                            if (expected_gender == "feminine" and "une" in suggestion.lower()) or \
                               (expected_gender == "feminine" and "ma" in suggestion.lower()) or \
                               (expected_gender == "masculine" and "un" in suggestion.lower()) or \
                               (expected_gender == "masculine" and "mon" in suggestion.lower()):
                                filtered_suggestions.append(suggestion)
                        error["suggestions"] = filtered_suggestions if filtered_suggestions else match.replacements
            print(f"Error: {error['error']}, Suggestions: {error['suggestions']}")
            errors.append(error)
        corrected_text = self.apply_corrections(text, matches, gender=gender)
        print(f"Final corrected text: {corrected_text}")
        return errors, corrected_text

    def analyze_speech(self, audio_file, gender="masculine"):
        audio, sr = librosa.load(audio_file, sr=16000)
        result = self.whisper_model.transcribe(audio_file, language='fr')
        text = result["text"].replace(',', '').lower()

        # Track pronunciation corrections
        pronunciation_corrections = []
        if 'alair' in text:
            text = text.replace('alair', 'aller')
            pronunciation_corrections.append({"error": "alair", "corrected": "aller"})
        if 'ecolay' in text:
            text = text.replace('ecolay', 'école')
            pronunciation_corrections.append({"error": "ecolay", "corrected": "école"})
        if 'j' in text:
            text = text.replace('j', 'Je')
            pronunciation_corrections.append({"error": "j", "corrected": "Je"})

        words = text.split()
        if words:
            words[0] = words[0].capitalize()
            text = ' '.join(words)
        print(f"Transcription: {text}")
        print(f"Pronunciation corrections: {pronunciation_corrections}")

        errors, corrected_text = self.analyze_text(text, gender=gender)
        print(f"Errors in order: {[error['error'] for error in errors]}")

        # Generate feedback text
        feedback_parts = []
        if pronunciation_corrections:
            feedback_parts.append("Pronunciation corrections:")
            for correction in pronunciation_corrections:
                feedback_parts.append(f"You pronounced {correction['error']} but it was corrected to {correction['corrected']}.")
        if errors and any(error['suggestions'] for error in errors):
            feedback_parts.append("Grammar corrections:")
            feedback_parts += [f"Change {error['error']} to {error['suggestions'][0]}" for error in errors if error['suggestions']]
        feedback_text = " ".join(feedback_parts) if feedback_parts else "No errors found."
        print(f"Feedback text: {feedback_text}")

        audio_path = self.generate_feedback_audio(feedback_text) if feedback_text.strip() else None

        features = self.extract_features(audio, sr)
        if self.classifier:
            accent = self.classifier.predict([features])[0]
            shap_values = self.shap_explainer.shap_values([features]) if self.shap_explainer else None
        else:
            accent = "Unknown"
            shap_values = None

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
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        return np.mean(mfccs.T, axis=0)

    def generate_feedback_audio(self, text, filename="app/static/correction_{}.mp3".format(uuid.uuid4())):
        try:
            if not text.strip():
                print("No feedback text to generate audio.")
                return None
            # Ensure directory exists and is writable
            static_dir = os.path.dirname(filename)
            os.makedirs(static_dir, exist_ok=True)
            if not os.access(static_dir, os.W_OK):
                os.chmod(static_dir, 0o755)  # Adjust permissions if needed

            # Preprocess text for phonetic clarity
            tts_text = text.replace("à l’", "a l").replace("à l", "a l")
            print(f"TTS text: {tts_text}")  # Debug log for TTS input

            # Use gTTS to generate audio
            tts = gTTS(tts_text, lang='fr', slow=False)
            tts.save(filename)
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"Audio saved to {filename} (Size: {file_size} bytes)")
                if file_size == 0:
                    print(f"Audio file {filename} is empty, not serving.")
                    os.unlink(filename)
                    return None
            else:
                print(f"Audio file {filename} not created.")
                return None
            return "/static/" + os.path.basename(filename) + "?t=" + str(time.time())  # Cache-busting timestamp
        except Exception as e:
            print(f"Error generating audio: {e}")
            return None
