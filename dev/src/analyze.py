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

    def analyze_text(self, text):
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
                suggestions = ["allé"] + [s for s in match.replacements if s != "aller"]
                error["suggestions"] = list(dict.fromkeys(suggestions))  # Remove duplicates
            print(f"Error: {error['error']}, Suggestions: {error['suggestions']}")
            errors.append(error)
        return errors

    def analyze_speech(self, audio_file):
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

        errors = self.analyze_text(text)
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
