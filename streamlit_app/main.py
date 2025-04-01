import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Campaign Manager", layout="wide")
st.title("📢 Campaign Content Manager")

# --- Step 1: Campaign Creation ---
st.header("1️⃣ Create a New Campaign")
with st.form("create_campaign"):
    title = st.text_input("Campaign Title")
    repeat_days = st.number_input("Repeat Every X Days", min_value=1, value=10)
    insight = st.text_input("Customer Insight")
    target_customer = st.text_input("Target Customer")
    description = st.text_area("Description")
    generation_mode = st.selectbox("Generation Mode", ["pre-batch", "just-in-time"])
    submit = st.form_submit_button("Create Campaign")

    if submit:
        res = requests.post(f"{API_BASE}/campaigns", json={
            "title": title,
            "repeat_every_days": repeat_days,
            "insight": insight,
            "target_customer": target_customer,
            "description": description,
            "generation_mode": generation_mode
        })
        if res.status_code == 200:
            st.success("✅ Campaign created!")
            st.rerun()
        else:
            st.error("❌ Failed to create campaign")

# --- Step 2: View Campaigns ---
st.header("2️⃣ Select Campaign")
res = requests.get(f"{API_BASE}/campaigns")
campaigns = res.json()
campaign_dict = {f"{c['id']} - {c['title']}": c['id'] for c in campaigns}
selected_label = st.selectbox("Campaign", list(campaign_dict.keys()))
campaign_id = campaign_dict[selected_label]

# --- Step 3: Generate Themes ---
st.header("3️⃣ Generate & Select Theme")
if st.button("🎯 Generate 5 Themes"):
    r = requests.post(f"{API_BASE}/themes/campaigns/{campaign_id}/generate_themes")
    if r.status_code == 200:
        st.success("Themes generated!")
        st.rerun()
    else:
        st.error("Theme generation failed.")

themes = requests.get(f"{API_BASE}/themes/campaigns/{campaign_id}").json()
for t in themes:
    st.subheader(f"📘 Theme {t['id']} - {t['title']}")
    st.markdown(t['story'])
    if not t['is_selected']:
        if st.button("✅ Select This Theme", key=f"select_theme_{t['id']}"):
            requests.post(f"{API_BASE}/themes/{t['id']}/select")
            st.success(f"Theme {t['id']} selected. Generating posts...")
            st.rerun()
    else:
        st.markdown("🟢 **Selected Theme**")

# --- Step 4: View & Manage Posts ---
st.header("4️⃣ Review & Manage Content Posts")
posts = requests.get(f"{API_BASE}/content/campaigns/{campaign_id}/posts").json()
for post in posts:
    st.markdown(f"### 📝 Post {post['id']}")
    st.text_area("Content", value=post['content'], height=150, key=f"content_{post['id']}")
    st.markdown(f"**Status:** `{post['status']}`")
    col1, col2, col3 = st.columns(3)
    if col1.button("✅ Approve", key=f"approve_{post['id']}"):
        requests.post(f"{API_BASE}/content/{post['id']}/approve")
        st.rerun()
    if col2.button("❌ Disapprove", key=f"disapprove_{post['id']}"):
        requests.post(f"{API_BASE}/content/{post['id']}/disapprove")
        st.rerun()
    if col3.button("🔁 Redo", key=f"redo_{post['id']}"):
        requests.post(f"{API_BASE}/content/{post['id']}/redo")
        st.rerun()
    st.divider()
