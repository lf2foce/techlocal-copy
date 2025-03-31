import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.title("📊 Campaign Content Review")

# Fetch campaigns safely
response = requests.get(f"{API_BASE}/campaigns/")
if response.status_code != 200:
    st.error("Failed to load campaigns.")
    st.stop()

campaigns = response.json()
if isinstance(campaigns, dict) and 'data' in campaigns:
    campaigns = campaigns['data']

campaign_options = {
    f"{c.get('id')} - {c.get('title')}": c.get("id")
    for c in campaigns if isinstance(c, dict)
}

campaign_name = st.selectbox("Select Campaign", list(campaign_options.keys()))
campaign_id = campaign_options[campaign_name]

# Fetch posts
posts = requests.get(f"{API_BASE}/content/campaigns/{campaign_id}/posts").json()

# Show posts
for post in posts:
    st.markdown(f"### 📝 Post {post['id']}")
    st.text_area("Content", value=post['content'], height=150, key=f"content_{post['id']}")
    st.markdown(f"**Status:** `{post['status']}`")

    col1, col2, col3 = st.columns(3)
    if col1.button("✅ Approve", key=f"approve_{post['id']}"):
        requests.post(f"{API_BASE}/content/{post['id']}/approve")
        st.success(f"Post {post['id']} approved")
        st.experimental_rerun()

    if col2.button("❌ Disapprove", key=f"disapprove_{post['id']}"):
        requests.post(f"{API_BASE}/content/{post['id']}/disapprove")
        st.warning(f"Post {post['id']} disapproved")
        st.experimental_rerun()

    if col3.button("🔁 Redo", key=f"redo_{post['id']}"):
        requests.post(f"{API_BASE}/content/{post['id']}/redo")
        st.info(f"Post {post['id']} regenerated")
        st.experimental_rerun()

    st.markdown("---")