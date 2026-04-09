import streamlit as st
import difflib
import os

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Pro Word Processor",
    page_icon="✍️",
    layout="centered"
)

# ─────────────────────────────────────────────
#  DATASET LOADING
# ─────────────────────────────────────────────
DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")

@st.cache_data
def load_dataset():
    custom_dict   = {}
    correct_words = set()
    files_loaded  = []

    if not os.path.isdir(DATASET_DIR):
        return custom_dict, correct_words, files_loaded

    for fname in os.listdir(DATASET_DIR):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(DATASET_DIR, fname)
        count = 0
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
                        custom_dict[wrong] = correct
                        correct_words.add(correct)
                        count += 1
        files_loaded.append(f"{fname} ({count} pairs)")

    return custom_dict, correct_words, files_loaded


def get_fuzzy_suggestion(word, custom_dict, correct_words, cutoff=0.6):
    all_knowns = list(custom_dict.keys()) + list(correct_words)
    matches = difflib.get_close_matches(word, all_knowns, n=1, cutoff=cutoff)
    if not matches:
        return None
    best = matches[0]
    return custom_dict[best] if best in custom_dict else best


def check_text(text, custom_dict, correct_words):
    results = []
    words   = text.split()
    for raw_word in words:
        cleaned = raw_word.strip(".,!?()\"';:-").lower()
        if not cleaned or not cleaned.isalpha():
            results.append({"original": raw_word, "cleaned": cleaned, "status": "ok", "suggestion": None})
            continue

        if cleaned in custom_dict:
            results.append({"original": raw_word, "cleaned": cleaned,
                            "status": "typo", "suggestion": custom_dict[cleaned]})
        elif cleaned in correct_words:
            results.append({"original": raw_word, "cleaned": cleaned, "status": "ok", "suggestion": None})
        else:
            suggestion = get_fuzzy_suggestion(cleaned, custom_dict, correct_words)
            results.append({"original": raw_word, "cleaned": cleaned,
                            "status": "unknown", "suggestion": suggestion})
    return results


# ─────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────
st.title("✍️ Pro Word Processor")
st.markdown("A smart spelling correction tool powered by your custom dataset.")

# Load dataset
custom_dict, correct_words, files_loaded = load_dataset()

# Dataset status
with st.expander("📂 Dataset Info", expanded=False):
    if files_loaded:
        st.success(f"✅ {len(files_loaded)} file(s) loaded — {len(custom_dict)} word pairs total")
        for f in files_loaded:
            st.markdown(f"• {f}")
    else:
        st.warning("⚠️ No dataset files found in the dataset/ folder.")

st.divider()

# Text input
text_input = st.text_area(
    "📝 Type or paste your text here:",
    height=200,
    placeholder="Type something with spelling mistakes like: teh recieve speling..."
)

col1, col2 = st.columns(2)
check_btn    = col1.button("🔍 Check Spelling", use_container_width=True)
autofix_btn  = col2.button("🔄 Auto-Fix All Typos", use_container_width=True)

st.divider()

# ─────────────────────────────────────────────
#  CHECK SPELLING
# ─────────────────────────────────────────────
if check_btn and text_input.strip():
    results  = check_text(text_input, custom_dict, correct_words)
    typos    = [r for r in results if r["status"] == "typo"]
    unknowns = [r for r in results if r["status"] == "unknown"]

    # Summary
    st.subheader("📊 Results")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Words",   len(results))
    c2.metric("❌ Typos Found", len(typos))
    c3.metric("⚠️ Unknown",    len(unknowns))

    # Highlighted text
    st.subheader("📄 Highlighted Text")
    highlighted = ""
    for r in results:
        if r["status"] == "typo":
            highlighted += f'<span style="background:#721c24;color:#f8d7da;padding:2px 4px;border-radius:4px;margin:2px">{r["original"]}</span> '
        elif r["status"] == "unknown":
            highlighted += f'<span style="background:#856404;color:#fff3cd;padding:2px 4px;border-radius:4px;margin:2px">{r["original"]}</span> '
        else:
            highlighted += f'{r["original"]} '

    st.markdown(
        f'<div style="background:#1e1e1e;padding:15px;border-radius:10px;line-height:2.2">{highlighted}</div>',
        unsafe_allow_html=True
    )

    # Legend
    st.markdown("""
    <small>
    🟥 = Typo (correction available) &nbsp;&nbsp;
    🟨 = Unknown word (fuzzy suggestion) &nbsp;&nbsp;
    ⬜ = Correct
    </small>
    """, unsafe_allow_html=True)

    # Suggestions table
    if typos or unknowns:
        st.subheader("💡 Suggestions")
        for r in typos + unknowns:
            icon = "❌" if r["status"] == "typo" else "⚠️"
            label = "Typo" if r["status"] == "typo" else "Unknown"
            if r["suggestion"]:
                st.markdown(f'{icon} **{r["original"]}** → ✅ `{r["suggestion"]}`')
            else:
                st.markdown(f'{icon} **{r["original"]}** — no suggestion found')

# ─────────────────────────────────────────────
#  AUTO FIX
# ─────────────────────────────────────────────
if autofix_btn and text_input.strip():
    results   = check_text(text_input, custom_dict, correct_words)
    fixed_words = []
    fix_count   = 0

    for r in results:
        if r["status"] == "typo" and r["suggestion"]:
            # Preserve capitalisation
            original = r["original"].strip(".,!?()\"';:-")
            suffix   = r["original"][len(original):]
            prefix   = r["original"][:len(r["original"]) - len(original.lstrip()) - len(suffix)]
            corrected = r["suggestion"]
            if original.isupper():
                corrected = corrected.upper()
            elif original[0].isupper():
                corrected = corrected.capitalize()
            fixed_words.append(corrected + suffix)
            fix_count += 1
        else:
            fixed_words.append(r["original"])

    fixed_text = " ".join(fixed_words)

    st.subheader("✅ Auto-Fixed Text")
    st.success(f"Fixed {fix_count} typo(s)!")
    st.text_area("Corrected text (copy from here):", value=fixed_text, height=200)
