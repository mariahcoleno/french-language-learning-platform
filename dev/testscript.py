from gtts import gTTS
tts = gTTS("Bonjour", lang='fr')
tts.save("test.mp3")
