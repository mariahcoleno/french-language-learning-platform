import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, render_template, request, jsonify, send_from_directory
from src.analyze import FrenchAnalyzer

app = Flask(__name__, static_folder=os.path.abspath('app/static'))
analyzer = FrenchAnalyzer()
app.config['UPLOAD_FOLDER'] = 'app/uploads'

PRELOADED_SENTENCES = [
    "Je vais à le marché.",
    "Je suis aller chez mon mère.",
    "Elle mange un pomme."
]

@app.route('/')
def index():
    return render_template('index.html', sentences=PRELOADED_SENTENCES)

@app.route('/analyze', methods=['POST'])
def analyze():
    recruiter_mode = request.form.get('recruiter_mode') == 'true'
    if 'audio' in request.files:
        audio = request.files['audio']
        if audio.filename == '':
            return jsonify({"error": "No audio file provided"}), 400
        filename = os.path.join(app.config['UPLOAD_FOLDER'], 'input.wav')
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        audio.save(filename)
        result = analyzer.analyze_speech(filename)
    else:
        text = request.form.get('text', '')
        if not text:
            return jsonify({"error": "No text provided"}), 400
        result = {
            "transcription": text,
            "errors": analyzer.analyze_text(text),
            "accent": "N/A",
            "shap_values": None,
            "audio_path": None,
            "pronunciation_corrections": []
        }

    return jsonify({
        "transcription": result["transcription"],
        "errors": result["errors"],
        "accent": result["accent"],
        "audio": result.get("audio_path"),
        "pronunciation_corrections": result.get("pronunciation_corrections", []),
        "recruiter_mode": recruiter_mode
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    static_path = os.path.join(app.static_folder, filename)
    print(f"Serving file: {static_path}, Exists: {os.path.exists(static_path)}")
    if os.path.exists(static_path):
        return send_from_directory(app.static_folder, filename)
    return "File not found", 404

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
