import whisper

model = whisper.load_model("base")
result = model.transcribe("/Users/mariahcoleno/Documents/FrenchLearningFeedbackEngine/dev/test.wav", language='fr', verbose=True)
print(result["text"])
