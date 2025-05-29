import language_tool_python

tool = language_tool_python.LanguageTool('fr')
text = "Je suis aller à école"
matches = tool.check(text)

for match in matches:
    error = text[match.offset: match.offset + match.errorLength]
    print(f"Error: {error}")
    print(f"Suggestions: {match.replacements}")
    print(f"Message: {match.message}")
    print("---")

tool.close()
