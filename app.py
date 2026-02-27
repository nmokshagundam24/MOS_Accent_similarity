import streamlit as st
import pandas as pd
import random
import os
import json
import hashlib
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

# ==============================
# CONFIG
# ==============================

TOTAL_TRIALS = 50
SPREADSHEET_NAME = "Accent_Similarity_MOS_Data"

st.set_page_config(page_title="Accent Similarity Study", layout="centered")
st.markdown("""
<style>

/* Disabled button - Grey */
div.stButton > button:disabled {
    background-color: #808080 !important;
    color: white !important;
    border: none !important;
}

/* Enabled button - Green */
div.stButton > button:not(:disabled) {
    background-color: #16a34a !important;
    color: white !important;
    border: none !important;
}

/* Slightly larger button */
div.stButton > button {
    height: 3em;
    width: 150px;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(BASE_DIR, "trials.csv"))

# ==============================
# GOOGLE SHEETS CONNECTION
# ==============================

def connect_sheet():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(credentials)
    return client.open(SPREADSHEET_NAME).worksheet("responses")

sheet = connect_sheet()

# ==============================
# HELPER FUNCTIONS
# ==============================

def generate_participant_id(name):
    clean_name = name.strip().replace(" ", "_").upper()
    hash_id = hashlib.md5(clean_name.encode()).hexdigest()[:6]
    return f"{clean_name}_{hash_id}"

def load_progress(pid):
    records = sheet.get_all_records()
    user_rows = [r for r in records if r["participant_id"] == pid]

    if not user_rows:
        return None

    last_trial = max(r["trial_index"] for r in user_rows)
    completed = any(r["completed"] == True for r in user_rows)

    return {
        "trial_index": last_trial + 1,
        "completed": completed
    }

def save_response(row):
    sheet.append_row(row)

# ==============================
# SESSION INIT
# ==============================

if "participant_id" not in st.session_state:
    st.session_state.participant_id = None

if "trial_order" not in st.session_state:
    st.session_state.trial_order = None

if "trial_index" not in st.session_state:
    st.session_state.trial_index = 0

# ==============================
# INSTRUCTIONS
# ==============================

if st.session_state.participant_id is None:

    st.title("Accent Similarity Study")

    st.markdown("""
## Instructions

Welcome to the Accent Similarity Study.

There are **50 total trials** in this study.

In each trial, you will see the **transcript of the sentence** on the screen.  
You will then hear:

- **One reference recording** (representing a particular accent)
- **Two synthesized samples: Sample A and Sample B**

Your task is to compare **each sample (A and B)** to the reference recording and rate:

> How similar does this sample sound to the reference accent?

You will rate **Sample A and Sample B separately**, using a 1–5 scale.

---

### Rating Scale

1 = Very Different Accent  
2 = Somewhat Different  
3 = Moderately Similar  
4 = Very Similar  
5 = Almost Identical Accent  

---

### Important Guidelines

Focus only on **accent similarity**.

Ignore:
- Speaker identity  
- Voice quality  
- Audio quality  
- Naturalness  
- Background noise  

Many recordings contain slight noise or reduced clarity.  
Please focus specifically on pronunciation patterns rather than recording quality.

Pay attention to:
- Word-level pronunciation  
- Phrase-level pronunciation  

---

### Additional Information

- Estimated completion time: **40–50 minutes** (in one sitting)
- Recommended to take it in multiple sittings; where each sitting: 10-15 trials. 
- You may replay audio as many times as needed
- Headphones are strongly recommended

If you accidentally refresh the page, simply enter your name again and you will **resume from where you left off**.

When you are ready, enter your name and click **Start / Resume**.
""")
#     st.markdown("""
# Focus only on accent similarity.

# Ignore:
# - Speaker identity
# - Voice quality
# - Audio quality
# - Naturalness
# - Background noise

# Pay attention to:
# - Word/Phrase level Pronunciation

# Scale:
# 1 = Very Different  
# 5 = Very Similar
# """)

    name_input = st.text_input("Enter your name:")

    if st.button("Start / Resume"):

        if name_input.strip() == "":
            st.warning("Name required.")
        else:
            pid = generate_participant_id(name_input)
            st.session_state.participant_id = pid

            progress = load_progress(pid)

            if progress:
                if progress["completed"]:
                    st.success("You have already completed this study.")
                    st.stop()

                st.session_state.trial_index = progress["trial_index"]
            else:
                indices = list(range(len(df)))
                random.shuffle(indices)
                st.session_state.trial_order = indices
                st.session_state.trial_index = 0

            indices = list(range(len(df)))
            random.seed(pid)
            random.shuffle(indices)
            st.session_state.trial_order = indices

            st.rerun()

    st.stop()

# ==============================
# TRIAL
# ==============================

trial_pos = st.session_state.trial_index

if trial_pos >= TOTAL_TRIALS:
    st.success("Study complete. Thank you.")
    st.stop()

row_index = st.session_state.trial_order[trial_pos]
trial = df.iloc[row_index]

st.markdown(f"## Trial {trial_pos + 1} of {TOTAL_TRIALS}")
st.progress((trial_pos + 1) / TOTAL_TRIALS)

st.markdown(f"**Sentence:** {trial['transcript']}")

anchors = [
    ("Native Accent", trial["native_path"]),
    ("Indian Accent", trial["indian_path"])
]

ratings = {}

for anchor_label, anchor_path in anchors:

    st.markdown("---")
    st.markdown(f"### Reference: {anchor_label}")
    st.audio(anchor_path)

    cols = st.columns(2)

    for i, (sample_label, sample_path) in enumerate([
        ("Sample A", trial["A_path"]),
        ("Sample B", trial["B_path"])
    ]):
        with cols[i]:
            st.markdown(f"#### {sample_label}")
            st.audio(sample_path)

            options = [
                (1, "1  —  Very Different"),
                (2, "2"),
                (3, "3"),
                (4, "4"),
                (5, "5  —  Very Similar"),
            ]

            rating = st.radio(
                f"How similar is {sample_label} to the {anchor_label}?",
                options,
                format_func=lambda x: x[1],
                index=None,
                key=f"{anchor_label}_{sample_label}_{trial_pos}"
            )

            # Store only numeric value
            ratings[f"{anchor_label}_{sample_label}"] = rating[0] if rating else None

            st.markdown(
                """<div style="display:flex; justify-content:space-between; font-size:14px; margin-top:-10px;">
                <span>Very Different</span>
                <span>Very Similar</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            ratings[f"{anchor_label}_{sample_label}"] = rating

# Check that all ratings are selected
all_rated = all(v is not None for v in ratings.values())

# Single Next button (grey until complete, green when ready)
next_button = st.button("Next", disabled=not all_rated)

if next_button:

    clean_ratings = {k: int(v) for k, v in ratings.items()}

    row = [
        str(st.session_state.participant_id),
        str(st.session_state.participant_id.split("_")[0]),
        int(trial_pos),
        str(trial["trial_id"]),
        str(trial["transcript"]),
        json.dumps(clean_ratings),
        datetime.now().isoformat(),
        False
    ]

    save_response(row)

    st.session_state.trial_index += 1
    st.rerun()
