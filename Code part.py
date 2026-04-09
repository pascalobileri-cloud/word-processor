import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import difflib

# ─────────────────────────────────────────────
#  DATASET FOLDER (sits next to this script)
# ─────────────────────────────────────────────
import sys
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR  = os.path.join(SCRIPT_DIR, "dataset")


class SpellCheckApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Pro Word Processor")
        self.geometry("780x660")
        self.custom_dict    = {}   # wrong  -> correct
        self.correct_words  = set()
        self.suggestion_popup = None

        self.tabview = ctk.CTkTabview(self, width=740, height=610)
        self.tabview.pack(padx=20, pady=20)

        self.tab_editor  = self.tabview.add("Editor")
        self.tab_dataset = self.tabview.add("Dataset Info")

        self.setup_editor_tab()
        self.setup_dataset_tab()

        # Auto-load on startup
        self.load_dataset_folder(silent=True)

    # ──────────────────────────────────────────
    #  EDITOR TAB
    # ──────────────────────────────────────────
    def setup_editor_tab(self):
        ctk.CTkLabel(self.tab_editor, text="Word Processor",
                     font=("Arial", 22, "bold")).pack(pady=10)

        self.input_box = ctk.CTkTextbox(self.tab_editor, width=680, height=280,
                                        font=("Arial", 14))
        self.input_box.tag_config("typo",     background="#721c24", foreground="#f8d7da")
        self.input_box.tag_config("not_found",background="#856404", foreground="#fff3cd")
        self.input_box.pack(pady=10)
        self.input_box.bind("<Button-1>", self.on_text_click)

        btn_frame = ctk.CTkFrame(self.tab_editor, fg_color="transparent")
        btn_frame.pack(pady=8)
        ctk.CTkButton(btn_frame, text="🔍 Highlight Typos",
                      command=self.highlight_typos).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text="🔄 Auto-Fix All Typos",
                      fg_color="#6f42c1", hover_color="#5a32a3",
                      command=self.auto_fix_all).grid(row=0, column=1, padx=5)
        ctk.CTkButton(btn_frame, text="💾 Save As",
                      fg_color="#28a745", hover_color="#1e7e34",
                      command=self.save_file).grid(row=0, column=2, padx=5)

        self.status_label = ctk.CTkLabel(
            self.tab_editor,
            text="💡 Dataset auto-loads from the 'dataset/' folder next to this script.",
            font=("Arial", 11), text_color="gray")
        self.status_label.pack(pady=4)

        # Legend
        leg = ctk.CTkFrame(self.tab_editor, fg_color="transparent")
        leg.pack()
        ctk.CTkLabel(leg, text="■", text_color="#f8d7da", font=("Arial", 14)).grid(row=0, column=0, padx=2)
        ctk.CTkLabel(leg, text="= Typo (suggestion available)", font=("Arial", 11), text_color="gray").grid(row=0, column=1, padx=2)
        ctk.CTkLabel(leg, text="■", text_color="#fff3cd", font=("Arial", 14)).grid(row=0, column=2, padx=(12, 2))
        ctk.CTkLabel(leg, text="= Not in dataset (fuzzy suggestion)", font=("Arial", 11), text_color="gray").grid(row=0, column=3, padx=2)

    # ──────────────────────────────────────────
    #  DATASET TAB
    # ──────────────────────────────────────────
    def setup_dataset_tab(self):
        card = ctk.CTkFrame(self.tab_dataset, corner_radius=15)
        card.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(card, text="Dataset Folder", font=("Arial", 18, "bold")).pack(pady=10)

        self.folder_label = ctk.CTkLabel(
            card,
            text=f"📁 Folder: {DATASET_DIR}",
            font=("Arial", 12), text_color="lightblue", wraplength=600)
        self.folder_label.pack(pady=6, padx=20)

        ctk.CTkLabel(
            card,
            text=(
                "Place one or more .txt files inside the dataset/ folder.\n"
                "Each line should be:   wrong → correct\n\n"
                "Example:\n"
                "  recieve → receive\n"
                "  teh → the\n"
                "  speling → spelling"
            ),
            justify="left", font=("Arial", 13)
        ).pack(pady=10, padx=20)

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(pady=6)
        ctk.CTkButton(btn_row, text="🔄 Reload Dataset Folder",
                      command=self.load_dataset_folder,
                      fg_color="#1f538d").grid(row=0, column=0, padx=6)
        ctk.CTkButton(btn_row, text="📂 Open Folder",
                      command=self.open_dataset_folder,
                      fg_color="#495057").grid(row=0, column=1, padx=6)

        self.dataset_label     = ctk.CTkLabel(card, text="", font=("Arial", 12), text_color="gray")
        self.dataset_label.pack(pady=4)
        self.word_count_label  = ctk.CTkLabel(card, text="", font=("Arial", 12), text_color="gray")
        self.word_count_label.pack(pady=2)
        self.files_label       = ctk.CTkLabel(card, text="", font=("Arial", 11), text_color="gray",
                                              wraplength=600, justify="left")
        self.files_label.pack(pady=4, padx=20)

    # ──────────────────────────────────────────
    #  DATASET LOADING
    # ──────────────────────────────────────────
    def load_dataset_folder(self, silent=False):
        """Read every *.txt in DATASET_DIR and merge into custom_dict."""
        if not os.path.isdir(DATASET_DIR):
            os.makedirs(DATASET_DIR, exist_ok=True)
            msg = f"Created empty dataset/ folder at:\n{DATASET_DIR}\n\nAdd .txt files there."
            if not silent:
                messagebox.showinfo("Dataset folder created", msg)
            self.status_label.configure(text="📂 dataset/ folder created — add .txt word-pair files.")
            return

        self.custom_dict   = {}
        self.correct_words = set()
        loaded_files       = []
        total_errors       = 0

        for fname in os.listdir(DATASET_DIR):
            if not fname.endswith(".txt"):
                continue
            fpath  = os.path.join(DATASET_DIR, fname)
            errors = 0
            count  = 0
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "→" in line:
                        parts = line.split("→")
                        if len(parts) == 2:
                            wrong   = parts[0].strip().lower()
                            correct = parts[1].strip().lower()
                            self.custom_dict[wrong] = correct
                            self.correct_words.add(correct)
                            count += 1
                        else:
                            errors += 1
                    else:
                        errors += 1
            loaded_files.append(f"• {fname} ({count} pairs{', ' + str(errors) + ' skipped' if errors else ''})")
            total_errors += errors

        # Update UI
        n = len(self.custom_dict)
        if loaded_files:
            self.dataset_label.configure(
                text=f"✅ {len(loaded_files)} file(s) loaded — {n} word pairs total",
                text_color="lightgreen")
            self.files_label.configure(text="\n".join(loaded_files))
            self.status_label.configure(
                text=f"✅ {n} word pairs ready. Click Highlight Typos to check your text.")
        else:
            self.dataset_label.configure(text="⚠️ No .txt files found in dataset/", text_color="orange")
            self.files_label.configure(text="")
            self.status_label.configure(text="⚠️ Add .txt word-pair files to the dataset/ folder.")

        self.word_count_label.configure(
            text=f"Total errors skipped across all files: {total_errors}" if total_errors else "")

    def open_dataset_folder(self):
        os.makedirs(DATASET_DIR, exist_ok=True)
        # Works on Windows; adapt for macOS/Linux if needed
        try:
            os.startfile(DATASET_DIR)
        except AttributeError:
            import subprocess
            subprocess.Popen(["xdg-open", DATASET_DIR])

    # ──────────────────────────────────────────
    #  FUZZY SUGGESTION ENGINE
    # ──────────────────────────────────────────
    def get_fuzzy_suggestion(self, word, cutoff=0.6):
        """
        Return the best matching correct word from the dataset using
        difflib's SequenceMatcher, or None if no close match is found.
        Priority:
          1. Exact key in custom_dict  (already handled upstream)
          2. Close match among custom_dict keys  (likely a variant typo)
          3. Close match among correct_words      (user wrote something near-correct)
        """
        all_knowns = list(self.custom_dict.keys()) + list(self.correct_words)
        matches = difflib.get_close_matches(word, all_knowns, n=3, cutoff=cutoff)
        if not matches:
            return None

        # Resolve: if the best match is itself a typo key, return its correction
        best = matches[0]
        if best in self.custom_dict:
            return self.custom_dict[best]
        return best   # it's already a correct word

    # ──────────────────────────────────────────
    #  HIGHLIGHTING
    # ──────────────────────────────────────────
    def highlight_typos(self):
        self.close_popup()

        if not self.custom_dict:
            self.status_label.configure(
                text="⚠️ No dataset loaded. Go to Dataset Info and reload.")
            return

        self.input_box.tag_remove("typo",      "1.0", "end")
        self.input_box.tag_remove("not_found", "1.0", "end")

        text  = self.input_box.get("1.0", "end-1c")
        words = text.split()

        for raw_word in words:
            cleaned = raw_word.strip(".,!?()\"';:-").lower()
            if not cleaned or not cleaned.isalpha():
                continue

            if cleaned in self.custom_dict:
                tag = "typo"
            elif cleaned in self.correct_words:
                continue   # correctly spelled word in our dataset
            else:
                tag = "not_found"

            # Highlight every occurrence
            start_pos = "1.0"
            while True:
                start_pos = self.input_box.search(
                    cleaned, start_pos, stopindex="end", nocase=True)
                if not start_pos:
                    break
                end_pos = f"{start_pos}+{len(cleaned)}c"
                self.input_box.tag_add(tag, start_pos, end_pos)
                start_pos = end_pos

    # ──────────────────────────────────────────
    #  AUTO-FIX ALL
    # ──────────────────────────────────────────
    def auto_fix_all(self):
        self.close_popup()
        if not self.custom_dict:
            self.status_label.configure(text="⚠️ No dataset loaded.")
            return

        text  = self.input_box.get("1.0", "end-1c")
        words = text.split()
        fixed = 0

        new_words = []
        for raw_word in words:
            stripped = raw_word.strip(".,!?()\"';:-")
            cleaned  = stripped.lower()
            prefix   = raw_word[: raw_word.find(stripped[0])] if stripped else ""
            suffix   = raw_word[len(prefix) + len(stripped):]

            if cleaned in self.custom_dict:
                corrected = self.custom_dict[cleaned]
                # Preserve original capitalisation style
                if stripped.isupper():
                    corrected = corrected.upper()
                elif stripped[0].isupper():
                    corrected = corrected.capitalize()
                new_words.append(prefix + corrected + suffix)
                fixed += 1
            else:
                new_words.append(raw_word)

        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", " ".join(new_words))
        self.highlight_typos()
        self.status_label.configure(text=f"✅ Auto-fixed {fixed} known typo(s).")

    # ──────────────────────────────────────────
    #  CLICK HANDLER
    # ──────────────────────────────────────────
    def on_text_click(self, event):
        self.close_popup()

        index = self.input_box.index(f"@{event.x},{event.y}")
        tags  = self.input_box.tag_names(index)

        ws = self.input_box.index(f"{index} wordstart")
        we = self.input_box.index(f"{index} wordend")
        clicked_word = self.input_box.get(ws, we).strip(".,!?()\"';:-").lower()

        if "typo" in tags:
            suggestion = self.custom_dict.get(clicked_word)
            self.show_suggestion_popup(event.x_root, event.y_root,
                                       clicked_word, ws, we, suggestion,
                                       kind="typo")
        elif "not_found" in tags:
            suggestion = self.get_fuzzy_suggestion(clicked_word)
            self.show_suggestion_popup(event.x_root, event.y_root,
                                       clicked_word, ws, we, suggestion,
                                       kind="not_found")

    # ──────────────────────────────────────────
    #  POPUP
    # ──────────────────────────────────────────
    def show_suggestion_popup(self, x, y, original_word, ws, we, suggestion, kind):
        self.suggestion_popup = ctk.CTkToplevel(self)
        self.suggestion_popup.wm_overrideredirect(True)
        self.suggestion_popup.geometry(f"+{x+12}+{y+12}")
        self.suggestion_popup.attributes("-topmost", True)

        frame = ctk.CTkFrame(self.suggestion_popup, corner_radius=10, border_width=1)
        frame.pack(padx=2, pady=2)

        if kind == "typo":
            header = f'Typo detected: "{original_word}"'
            header_color = "#f8d7da"
        else:
            header = f'Unknown word: "{original_word}"'
            header_color = "#fff3cd"

        ctk.CTkLabel(frame, text=header,
                     font=("Arial", 12, "bold"),
                     text_color=header_color).pack(padx=12, pady=(10, 4))

        if suggestion:
            ctk.CTkLabel(frame, text="Did you mean:",
                         font=("Arial", 11), text_color="gray").pack(padx=12)
            ctk.CTkButton(
                frame,
                text=f"✔  {suggestion}",
                width=200,
                fg_color="#1f538d",
                hover_color="#144070",
                command=lambda: self.replace_word(ws, we, suggestion)
            ).pack(padx=12, pady=4)
        else:
            ctk.CTkLabel(frame,
                         text="No suggestion found in dataset.",
                         font=("Arial", 11), text_color="gray").pack(padx=12, pady=4)

        ctk.CTkButton(frame, text="✕ Dismiss", width=200,
                      fg_color="#495057", hover_color="#343a40",
                      command=self.close_popup).pack(padx=12, pady=(2, 10))

    # ──────────────────────────────────────────
    #  HELPERS
    # ──────────────────────────────────────────
    def replace_word(self, ws, we, suggestion):
        self.input_box.delete(ws, we)
        self.input_box.insert(ws, suggestion)
        self.close_popup()
        self.highlight_typos()

    def close_popup(self):
        if self.suggestion_popup:
            self.suggestion_popup.destroy()
            self.suggestion_popup = None

    def save_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text files", "*.txt"),
                                                       ("All files", "*.*")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.input_box.get("1.0", "end-1c"))
            self.status_label.configure(text=f"💾 Saved to {os.path.basename(path)}")


if __name__ == "__main__":
    app = SpellCheckApp()
    app.mainloop()
