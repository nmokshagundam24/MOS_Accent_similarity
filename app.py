import streamlit as st
import pandas as pd
import random
import os
import time
from datetime import datetime
import json
import hashlib

# ==============================
# CONFIG
# ==============================

TOTAL_TRIALS = 50
RESULTS_FOLDER = "results"

st.set_page_config(page_title="Accent Similarity Study", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRIALS_PATH = os.path.join(BASE_DIR, "trials.csv")

if not os.path.exists(RESULTS_FOLDER):
    os.makedirs(RESULTS_FOLDER)

# ==============================
# LOAD TRIALS
# ==============================

@st.cache_data
def load_trials():
    return pd.read_csv(TRIALS_PATH)

df = load_trials()

# ==============================
# SESSION INIT
# ==============================

if "participant_id" not in st.session_state:
    st.session_state.participant_id = None

if "trial_order" not in st.session_state:
    st.session_state.trial_order = None

if "trial_index" not in st.session_state:
    st.session_state.trial_index = 0

if "responses" not in st.session_state:
    st.session_state.responses = []

# ==============================
# LOAD PROGRESS IF EXISTS
# ==============================

def load_progress(pid):
    progress_file = os.path.join(RESULTS_FOLDER, f"{pid}_progress.json")

    if not os.path.exists(progress_file):
        return None

    try:
        with open(progress_file, "r") as f:
            data = json.load(f)
        return data
    except Exception:
        # Corrupted file — delete and reset
        os.remove(progress_file)
        return None

def save_progress(pid):
    progress_file = os.path.join(RESULTS_FOLDER, f"{pid}_progress.json")

    # Convert numpy types to native Python types
    clean_responses = []

    for r in st.session_state.responses:
        clean_r = {}
        for key, value in r.items():

            if isinstance(value, dict):
                clean_dict = {}
                for k2, v2 in value.items():
                    clean_dict[k2] = int(v2) if hasattr(v2, "item") else v2
                clean_r[key] = clean_dict

            else:
                clean_r[key] = int(value) if hasattr(value, "item") else value

        clean_responses.append(clean_r)

    data = {
        "trial_order": [int(x) for x in st.session_state.trial_order],
        "trial_index": int(st.session_state.trial_index),
        "responses": clean_responses
    }

    with open(progress_file, "w") as f:
        json.dump(data, f)

# ==============================
# INSTRUCTIONS PAGE
# ==============================

if st.session_state.participant_id is None:

    st.title("Accent Similarity Study")

    st.markdown("""
### Instructions

Welcome to the Accent Similarity Study.

Your task is to evaluate **accent similarity only**.

For each trial, you will hear:
- A reference accent recording
- Two synthesized speech samples

Your job is to rate how similar each synthesized sample sounds to the reference accent.

---

### Please focus only on:

- Pronunciation patterns  
- Vowel quality  
- Consonant articulation  

---

### Please ignore:

- Speaker identity  
- Voice quality  
- Gender  
- Audio quality  
- Naturalness  
- Background noise  

Some recordings may contain noise or reduced audio clarity.  
Please ignore these factors and focus strictly on accent-related aspects.

---

### Rating Scale (1–5)

1 = Very Different Accent  
2 = Somewhat Different  
3 = Moderately Similar  
4 = Very Similar  
5 = Almost Identical Accent  

---

You may replay the audio as many times as needed.

Recommended to take the study in one go. 
Approximated time: 40–50 minutes.

When ready, enter your name and click **Start / Resume**.
""")

    name_input = st.text_input("Enter your name:")

    if st.button("Start / Resume"):

        if name_input.strip() == "":
            st.warning("Name required.")
        else:
            # Clean name
            clean_name = name_input.strip().replace(" ", "_").upper()

            # Deterministic participant ID (same name = same ID)
            hash_id = hashlib.md5(clean_name.encode()).hexdigest()[:6]
            participant_id = f"{clean_name}_{hash_id}"

            st.session_state.participant_id = participant_id

            progress = load_progress(participant_id)

            if progress:
                st.session_state.trial_order = progress["trial_order"]
                st.session_state.trial_index = progress["trial_index"]
                st.session_state.responses = progress["responses"]
                st.success("Previous progress found. Resuming study.")
            else:
                indices = list(range(len(df)))
                random.shuffle(indices)
                st.session_state.trial_order = indices
                st.session_state.trial_index = 0
                st.session_state.responses = []
                st.success(f"New session started. Your participant ID: {participant_id}")

            st.rerun()

    st.stop()

# ==============================
# COMPLETION CHECK
# ==============================

if st.session_state.trial_index >= TOTAL_TRIALS:

    final_file = os.path.join(
        RESULTS_FOLDER,
        f"{st.session_state.participant_id}_final.csv"
    )

    pd.DataFrame(st.session_state.responses).to_csv(final_file, index=False)

    progress_file = os.path.join(
        RESULTS_FOLDER,
        f"{st.session_state.participant_id}_progress.json"
    )

    if os.path.exists(progress_file):
        os.remove(progress_file)

    st.title("Study Complete")
    st.write("Thank you for participating.")
    st.stop()

# ==============================
# CURRENT TRIAL
# ==============================

trial_pos = st.session_state.trial_index
row_index = st.session_state.trial_order[trial_pos]
trial = df.iloc[row_index]

st.markdown(f"## Trial {trial_pos + 1} of {TOTAL_TRIALS}")
st.progress((trial_pos + 1) / TOTAL_TRIALS)

st.markdown("---")
st.markdown(f"**Sentence:** _{trial['transcript']}_")
st.markdown("---")

# ==============================
# FREEZE ANCHOR ORDER
# ==============================

anchor_key = f"anchor_{trial_pos}"
if anchor_key not in st.session_state:
    st.session_state[anchor_key] = random.choice(["native_first", "indian_first"])

anchor_order = st.session_state[anchor_key]

if anchor_order == "native_first":
    anchors = [("Native Accent", trial["native_path"]),
               ("Indian Accent", trial["indian_path"])]
else:
    anchors = [("Indian Accent", trial["indian_path"]),
               ("Native Accent", trial["native_path"])]

all_selected = True

# ==============================
# RATING BLOCKS
# ==============================

for anchor_label, anchor_path in anchors:

    with st.container():
        st.markdown(f"### Reference: {anchor_label}")
        st.audio(os.path.join(BASE_DIR, anchor_path))

        st.markdown("Please listen carefully and rate both samples below:")

        ab_key = f"ab_{trial_pos}_{anchor_label}"
        if ab_key not in st.session_state:
            st.session_state[ab_key] = random.choice(["A_first", "B_first"])

        if st.session_state[ab_key] == "A_first":
            samples = [("Sample A", trial["A_path"]),
                       ("Sample B", trial["B_path"])]
        else:
            samples = [("Sample B", trial["B_path"]),
                       ("Sample A", trial["A_path"])]

        cols = st.columns(2)

        for i, (sample_label, sample_path) in enumerate(samples):
            with cols[i]:
                st.markdown(f"#### {sample_label}")
                st.audio(os.path.join(BASE_DIR, sample_path))

                rating_key = f"rating_{trial_pos}_{anchor_label}_{sample_label}"

                rating = st.radio(
                    "Accent Similarity Rating",
                    options=[1, 2, 3, 4, 5],
                    key=rating_key,
                    horizontal=True
                )

                st.markdown(
                    "<div style='display:flex; justify-content:space-between; font-size:12px;'>"
                    "<span>Very Different</span>"
                    "<span>Very Similar</span>"
                    "</div>",
                    unsafe_allow_html=True
                )

                if rating_key not in st.session_state:
                    all_selected = False

        st.markdown("---")

# ==============================
# NEXT BUTTON
# ==============================

st.button("Next", disabled=not all_selected, key="next_button")

if st.session_state.get("next_button"):

    response = {
        "trial_id": trial["trial_id"],
        "transcript": trial["transcript"],
        "ratings": {
            k: st.session_state[k]
            for k in st.session_state
            if k.startswith(f"rating_{trial_pos}_")
        },
        "timestamp": datetime.now().isoformat()
    }

    st.session_state.responses.append(response)
    st.session_state.trial_index += 1

    save_progress(st.session_state.participant_id)

    st.rerun()