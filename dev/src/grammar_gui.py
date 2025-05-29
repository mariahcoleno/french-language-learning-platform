import tkinter as tk
from tkinter import ttk, filedialog
import language_tool_python
import json
import os

tool = language_tool_python.LanguageTool('fr')
dataset = []

def check_grammar():
    text = input_text.get("1.0", tk.END).strip()
    matches = tool.check(text)

    for row in feedback_table.get_children():
        feedback_table.delete(row)

    errors = []
    for match in matches:
        error = text[match.offset: match.offset + match.errorLength]
        suggestions = ", ".join(match.replacements)
        message = match.message
        feedback_table.insert("", "end", values=(error, suggestions, message))
        errors.append(f"{error} → {suggestions}")

    dataset.append({
        "text": text,
        "errors": errors,
        "accent": "Unknown",
        "phonetics": "",
        "audio": ""
    })

def save_dataset():
    file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        status_label.config(text=f"Saved to {file_path}")

root = tk.Tk()
root.title("French Grammar Checker")
root.geometry("800x400")

input_label = tk.Label(root, text="Enter French text:")
input_label.pack(anchor="w", padx=10, pady=(10, 0))
input_text = tk.Text(root, height=5)
input_text.pack(fill="x", padx=10)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)
check_button = tk.Button(button_frame, text="Check Grammar", command=check_grammar)
check_button.pack(side="left", padx=5)
save_button = tk.Button(button_frame, text="Save Dataset", command=save_dataset)
save_button.pack(side="left", padx=5)

feedback_table = ttk.Treeview(root, columns=("Error", "Suggestions", "Explanation"), show="headings")
feedback_table.heading("Error", text="❌ Error")
feedback_table.heading("Suggestions", text="💡 Suggestions")
feedback_table.heading("Explanation", text="🧠 Explanation")
feedback_table.pack(fill="both", expand=True, padx=10, pady=10)

status_label = tk.Label(root, text="")
status_label.pack(anchor="w", padx=10)

root.mainloop()
