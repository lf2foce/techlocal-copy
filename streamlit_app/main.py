import streamlit as st
import requests

API_BASE = "https://techlocal-copy.onrender.com"
# API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="Campaign Manager", layout="wide")
st.title("📢 Campaign Content Manager")

# --- Step 1: Campaign Creation ---
st.header("1️⃣ Create a New Campaign")
with st.form("create_campaign"):
    title = st.text_input("Campaign Title", placeholder="Tên chiến dịch Marketing")
    repeat_days = st.number_input("Số bài viết cần tạo", min_value=1, value=10)
    insight = st.text_input("Customer Insight", placeholder="Insight chính: Họ áp lực phải thành công, nhưng cảm thấy đơn độc. Họ muốn trở thành một người đàn ông bản lĩnh – vừa mạnh mẽ, vừa tinh tế, vừa trách nhiệm.")
    target_customer = st.text_input("Target Customer", placeholder="Tệp khách hàng mục tiêu: Nam giới 25–40 tuổi, sống tại thành thị, có gia đình hoặc sự nghiệp đang phát triển, tìm kiếm sự cân bằng & bản lĩnh cá nhân.")
    description = st.text_area("Mô tả prompt", placeholder="Mô tả prompt cho tệp khách hàng mục tiêu")
    generation_mode = st.selectbox("Generation Mode", ["pre-batch", "just-in-time"])
    submit = st.form_submit_button("Create Campaign")

    if submit:
        if not title or not insight or not target_customer or not description:
            st.error("❌ Please fill in all required fields")
        else:
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
                st.session_state.show_campaign_management = True
                st.rerun()
            else:
                st.error("❌ Failed to create campaign")

# Initialize session state for campaign management
if 'show_campaign_management' not in st.session_state:
    st.session_state.show_campaign_management = False

# Show campaign management sections only after successful creation
if st.session_state.show_campaign_management:
    # --- Step 2: View Campaigns ---
    st.header("2️⃣ Select Campaign")
    res = requests.get(f"{API_BASE}/campaigns")
    campaigns = res.json()
    if campaigns:
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
    else:
        st.info("No campaigns found. Please create a new campaign.")
else:
    st.info("👆 Create a campaign above to start managing content.")
