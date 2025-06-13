"""
Flask web application for French language learning with grammar and pronunciation analysis.
Provides REST API endpoints for text and audio analysis with real-time feedback.
"""

import sys
import os

# Add parent directory to path for importing custom modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request, jsonify, send_from_directory
from src.analyze import FrenchAnalyzer

# Initialize Flask app with custom static folder path
app = Flask(__name__, static_folder=os.path.abspath('app/static'))

# Initialize French language analyzer
analyzer = FrenchAnalyzer()

# Configure upload directory for audio files
app.config['UPLOAD_FOLDER'] = 'app/uploads'

# Sample sentences with common French grammar errors for testing/demo
PRELOADED_SENTENCES = [
    "Je vais à le marché.",  # Should be "au marché" (contraction)
    "Je suis aller chez mon mère.",  # Should be "allé" (past participle agreement) and "ma mère" (gender)
    "Elle mange un pomme."  # Should be "une pomme" (gender agreement)
]

@app.route('/')
def index():
    """
    Renders the main page with preloaded sample sentences.
    """
    return render_template('index.html', sentences=PRELOADED_SENTENCES)

@app.route('/analyze_audio', methods=['POST'])
def analyze_audio():
    """
    Analyzes uploaded audio file for pronunciation and grammar errors.
    
    Expected form data:
    - audio: Audio file (WAV, MP3, etc.)
    - gender: 'masculine' or 'feminine' for grammar agreement
    - recruiter_mode: 'true' for demo mode with popup
    
    Returns JSON with transcription, errors, corrections, and accent analysis.
    """
    # Extract form parameters
    recruiter_mode = request.form.get('recruiter_mode') == 'true'
    gender = request.form.get('gender', 'masculine')
    
    # Validate audio file presence
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio = request.files['audio']
    if audio.filename == '':
        return jsonify({"error": "No audio file provided"}), 400
    
    # Save uploaded audio file
    filename = os.path.join(app.config['UPLOAD_FOLDER'], 'input.wav')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    audio.save(filename)
    
    # Analyze audio using French analyzer
    result = analyzer.analyze_speech(filename, gender=gender)
    
    # Prepare response with analysis results
    response = {
        "transcription": result["transcription"],
        "errors": result["errors"],
        "corrected_text": result["corrected_text"],
        "accent": result["accent"],
        "audio": result.get("audio_path"),
        "pronunciation_corrections": result.get("pronunciation_corrections", []),
        "recruiter_mode": recruiter_mode
    }
    
    # Add demo popup message for recruiter mode
    if recruiter_mode:
        response["popup"] = "This app provides grammar, accent, and pronunciation correction to help you improve your French."
    
    return jsonify(response)

@app.route('/analyze_text', methods=['POST'])
def analyze_text():
    """
    Analyzes submitted text for French grammar errors.
    
    Expected form data:
    - text: French text to analyze
    - gender: 'masculine' or 'feminine' for grammar agreement
    - recruiter_mode: 'true' for demo mode with popup
    
    Returns JSON with original text, detected errors, and corrections.
    """
    # Extract form parameters
    recruiter_mode = request.form.get('recruiter_mode') == 'true'
    gender = request.form.get('gender', 'masculine')
    text = request.form.get('text', '')
    
    # Validate text input
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    # Analyze text for grammar errors
    errors, corrected_text = analyzer.analyze_text(text, gender=gender)
    
    # Structure analysis results
    result = {
        "transcription": text,
        "errors": errors,
        "corrected_text": corrected_text,
        "accent": "N/A",  # Not applicable for text analysis
        "shap_values": None,
        "audio_path": None,
        "pronunciation_corrections": []
    }
    
    # Prepare consistent response format
    response = {
        "transcription": result["transcription"],
        "errors": result["errors"],
        "corrected_text": result["corrected_text"],
        "accent": result["accent"],
        "audio": result.get("audio_path"),
        "pronunciation_corrections": result.get("pronunciation_corrections", []),
        "recruiter_mode": recruiter_mode
    }
    
    # Add demo popup message for recruiter mode
    if recruiter_mode:
        response["popup"] = "This app provides grammar, accent, and pronunciation correction to help you improve your French."
    
    return jsonify(response)

@app.route('/static/<path:filename>')
def serve_static(filename):
    """
    Serves static files (CSS, JS, images) with debugging information.
    Custom route to handle static file serving with logging.
    """
    static_path = os.path.join(app.static_folder, filename)
    print(f"Serving file: {static_path}, Exists: {os.path.exists(static_path)}")
    
    if os.path.exists(static_path):
        return send_from_directory(app.static_folder, filename)
    return "File not found", 404

if __name__ == "__main__":
    # Run Flask development server
    # Host 0.0.0.0 allows external connections, port 5001 to avoid conflicts
    app.run(debug=True, host="0.0.0.0", port=5001)
