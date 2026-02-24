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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(BASE_DIR, "trials.csv"))

# ==============================
# GOOGLE SHEETS CONNECTION
# ==============================

def connect_sheet():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
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
Focus only on accent similarity.

Ignore:
- Speaker identity
- Voice quality
- Audio quality
- Naturalness
- Background noise

Pay attention to:
- Word/Phrase level Pronunciation

Scale:
1 = Very Different  
5 = Very Similar
""")

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

            rating = st.radio(
                "Accent Similarity Rating",
                [1,2,3,4,5],
                key=f"{anchor_label}_{sample_label}_{trial_pos}"
            )

            ratings[f"{anchor_label}_{sample_label}"] = rating

if st.button("Next"):

    row = [
        st.session_state.participant_id,
        st.session_state.participant_id.split("_")[0],
        trial_pos,
        trial["trial_id"],
        trial["transcript"],
        json.dumps(ratings),
        datetime.now().isoformat(),
        False
    ]

    save_response(row)

    st.session_state.trial_index += 1
    st.rerun()