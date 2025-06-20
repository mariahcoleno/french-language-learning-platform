import sys
import os

# Add parent directory to path for importing custom modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request, jsonify, send_from_directory
from src.analyze import FrenchAnalyzer

# Initialize Flask app with custom static folder path
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
print(f"Static folder: {app.static_folder}")

# Initialize French language analyzer
analyzer = FrenchAnalyzer()

# Configure upload directory for audio files
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Sample sentences with common French grammar errors for testing/demo - Now in French with explanations
PRELOADED_SENTENCES = [
    {
        "text": "Je vais à le marché.",
        "description": "Erreur de contraction - devrait être 'au marché'"
    },
    {
        "text": "Je suis aller chez mon mère.",
        "description": "Accord du participe passé et genre - devrait être 'allé' et 'ma mère'"
    },
    {
        "text": "Elle mange un pomme.",
        "description": "Accord de genre - devrait être 'une pomme'"
    },
    {
        "text": "Je mange à école.",
        "description": "Contraction manquante - devrait être 'à l'école'"
    },
    {
        "text": "Il est une belle fille.",
        "description": "Accord pronom-adjectif - devrait être 'Elle est une belle fille'"
    }
]

# French interface text
FRENCH_INTERFACE = {
    "page_title": "Analyseur de Français - Correction Grammaticale et Prononciation",
    "main_heading": "Analyseur de Langue Française",
    "description": "Améliorez votre français avec notre outil d'analyse grammaticale et de prononciation",
    "text_analysis_tab": "Analyse de Texte",
    "audio_analysis_tab": "Analyse Audio",
    "sample_sentences": "Phrases d'exemple :",
    "gender_label": "Genre du locuteur :",
    "gender_masculine": "Masculin",
    "gender_feminine": "Féminin",
    "text_input_placeholder": "Entrez votre texte français ici...",
    "analyze_button": "Analyser",
    "record_button": "Enregistrer",
    "upload_button": "Télécharger un fichier audio",
    "results_heading": "Résultats de l'analyse :",
    "transcription_label": "Transcription :",
    "errors_label": "Erreurs détectées :",
    "corrected_text_label": "Texte corrigé :",
    "accent_label": "Accent détecté :",
    "pronunciation_corrections_label": "Corrections de prononciation :",
    "no_errors": "Aucune erreur détectée. Excellent travail !",
    "demo_popup": "Cette application fournit des corrections grammaticales, d'accent et de prononciation pour vous aider à améliorer votre français.",
    "error_no_audio": "Aucun fichier audio fourni",
    "error_no_text": "Aucun texte fourni",
    "file_not_found": "Fichier non trouvé"
}

@app.route('/')
def index():
    """
    Renders the main page with preloaded sample sentences and French interface.
    """
    return render_template('index.html', 
                         sentences=PRELOADED_SENTENCES,
                         interface=FRENCH_INTERFACE)

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
        return jsonify({"error": FRENCH_INTERFACE["error_no_audio"]}), 400
    
    audio = request.files['audio']
    if audio.filename == '':
        return jsonify({"error": FRENCH_INTERFACE["error_no_audio"]}), 400
    
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
        "recruiter_mode": recruiter_mode,
        "interface": FRENCH_INTERFACE
    }
    
    # Add demo popup message for recruiter mode
    if recruiter_mode:
        response["popup"] = FRENCH_INTERFACE["demo_popup"]
    
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
        return jsonify({"error": FRENCH_INTERFACE["error_no_text"]}), 400
    
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
        "recruiter_mode": recruiter_mode,
        "interface": FRENCH_INTERFACE
    }
    
    # Add demo popup message for recruiter mode
    if recruiter_mode:
        response["popup"] = FRENCH_INTERFACE["demo_popup"]
    
    return render_template('index.html', 
                     sentences=PRELOADED_SENTENCES,
                     analysis_results=response,
                     original_text=text,
                     interface=FRENCH_INTERFACE)

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
    return FRENCH_INTERFACE["file_not_found"], 404

if __name__ == "__main__":
    # Run Flask development server
    # Host 0.0.0.0 allows external connections, port 5001 to avoid conflicts
    app.run(debug=True, host="0.0.0.0", port=5001)
