# French Learning Feedback Engine

### Overview
The French Learning Feedback Engine is a Flask-based application designed to help French learners improve their pronunciation and grammar. It transcribes spoken French, identifies errors, and provides personalized audio feedback using AI-powered tools like Whisper and gTTS.

### Features
- Real-time speech transcription with Whisper.
- Detection of pronunciation and grammar errors (e.g., "a" to "à l’" before "école").
- Custom audio feedback in French, generated with gTTS.
- Web interface for easy interaction.
- Audio support for transcribing WAV files.
- Explainability via an error table in the UI, showing errors, suggested corrections, and explanations.

### Files
- `src/analyze.py`: Processes audio or text input using Whisper for transcription and language_tool_python for grammar checks, generating personalized audio feedback with gTTS.
- `app/main.py`: Manages the Flask application, handling routes for the homepage and analysis requests while serving static files like audio feedback.
- `app/templates/index.html`: Provides the user interface with input fields for text or audio, buttons to trigger analysis, and a section to display feedback results.
- `requirements.txt`: Lists dependencies required to run scripts.
- `test.wav`: A sample audio file containing example input.

### Setup and Usage
#### Option 1: From GitHub (Clone)
- **NOTE**
  - Start in your preferred directory (e.g., cd ~/Desktop/ or cd ~/Documents/). 
1. Clone the repository: `git clone https://github.com/mariahcoleno/FrenchLearningFeedbackEngine.git`
2. Navigate to the project directory: `cd FrenchLearningFeedbackEngine/dev/`
3. Create a virtual environment: `python3.10 -m venv venv`
4. Activate the virtual environment: `source venv/bin/activate` # On Windows: venv\Scripts\activate
5. (Optional) Upgrade tools: pip install --upgrade pip setuptools wheel 
6. Install dependencies: `pip install -r requirements.txt`
   - If requirements.txt is missing, install manually: 
     `pip install flask==3.0.3 language-tool-python==2.9.3 torch>=2.4.0 transformers==4.44.2
      gTTS==2.5.3 openai-whisper==20240930 shap==0.46.0 librosa==0.10.2 scikit-learn==1.5.1 numpy==1.26.4 plotly==5.24.0`.
7. Proceed to "Run the App" below.

#### Option 2: Local Setup (Existing Repository)
1. Navigate to your local repository (adjust path as needed): `cd ~/Documents/FrenchLearningFeedbackEngine/dev`
2. Setup and activate a virtual environment:
   - If existing: `source venv/bin/activate` (adjust path if venv is elsewhere)
   - If new:
     - `python3.10 -m venv venv`
     - `source venv/bin/activate` # On Windows: venv\Scripts\activate
3. (Optional) Upgrade tools: pip install --upgrade pip setuptools wheel 
4. Install dependencies (if not already): `pip install -r requirements.txt` 
   - If requirements.txt is missing, use the manual install command above.
5. Proceed to "Run the App" below.

### Run the App (Both Options):
1. `python3 -m app.main` 
   - Access it at http://127.0.0.1:5000.
   - Stop the app with Ctrl+C when done.
2. Use the interface:
   - Enter text (or select from the dropdown) and click "Analyze Text".
   - Upload a .wav file (click "Choose File", select the file, click "Open", then "Analyze Speech").
   - View the transcription, pronunciation corrections, and an error table with errors, suggestions, and explanations.
   - Listen to the audio feedback from a French speaker addressing corrected pronunciation and grammar.  

### Sample Data
- Je vais à le marché.
- Je suis aller chez mon mère.
- Elle mange un pomme. 

### Project Structure
- FrenchLearningFeedbackEngine/
  - dev/
    - app/
      - main.py
      - templates/index.html
    - src/
      - __init__.py
      - analyze.py 
    - venv/ (Virtual environment, created during setup)
    - README.md
    - requirements.txt
    - test.wav
  - .git/ (Git repository files)

### Dependencies
- Listed in requirements.txt:
  - flask==3.0.3
  - language-tool-python==2.9.3
  - torch>=2.4.0
  - transformers==4.44.2
  - gTTS==2.5.3
  - openai-whisper==20240930
  - shap==0.46.0
  - librosa==0.10.2
  - scikit-learn==1.5.1
  - numpy==1.26.4
  - plotly==5.24.0

### Notes
- The virtual environment uses Python 3.10 for compatibility with specific library versions (e.g., Whisper) as some libraries may have issues with the system default (3.13). 
  - Check your Python version with: `python3 --version`
- Ensure an internet connection for gTTS to generate audio.

### License
This project is licensed under the MIT License. See the LICENSE file for details.
