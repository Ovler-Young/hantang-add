import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import text
import requests
import re
import time
from wbi import encWbi, getWbiKeys

st.header("Add Video")

if "clear_form" in st.session_state:
    st.session_state.bv_id = ""
    st.session_state.av_id = ""
    del st.session_state.clear_form

col1, col2 = st.columns(2)

with col1:
    bv_id = st.text_input(
        "Video BV ID",
        placeholder="format: BV[0-9a-zA-Z]{10} URL also works",
        key="bv_id",
        value=st.session_state.get("bv_id", ""),
    )

with col2:
    av_id = st.text_input(
        "Video AV ID",
        placeholder="format: [0-9]+ / av[0-9]+ URL also works",
        key="av_id",
        value=st.session_state.get("av_id", ""),
    )

if not bv_id and not av_id:
    st.markdown(
        "Please input a valid BV or AV ID. And don't forget to press enter to submit."
    )
    st.stop()

# Handle BV ID input
if bv_id:
    bv_match = re.search(r"BV[0-9a-zA-Z]{10}", bv_id)
    if bv_match:
        video_id = bv_match.group(0)
        param_key = "bvid"
        player_id = f"bvid={video_id}"
    else:
        st.warning("Invalid BV ID.")
        st.stop()
elif av_id:
    av_match = re.search(r"[0-9]+", av_id.lower())
    if av_match:
        video_id = av_match.group(0)
        param_key = "aid"
        player_id = f"aid={video_id}"
    else:
        st.warning("Invalid AV ID.")
        st.stop()

components.iframe(f"https://player.bilibili.com/player.html?{player_id}", height=400)

# Update signed params based on ID type
img_key, sub_key = getWbiKeys()
signed_params = encWbi(params={param_key: video_id}, img_key=img_key, sub_key=sub_key)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

response = requests.get(
    "https://api.bilibili.com/x/web-interface/wbi/view/detail",
    params=signed_params,
    headers=headers,
)

video_info = response.json()

# display video info
st.header(video_info["data"]["View"]["title"])

video_data = {
    "aid": video_info["data"]["View"]["aid"],
    "bvid": video_info["data"]["View"]["bvid"],
    "pubdate": video_info["data"]["View"]["pubdate"],
    "title": video_info["data"]["View"]["title"],
    "description": video_info["data"]["View"]["desc"],
    "tag": ";".join([tag["tag_name"] for tag in video_info["data"]["Tags"]]),
    "pic": video_info["data"]["View"]["pic"].replace("http://", "//"),
    "type_id": video_info["data"]["View"]["tid"],
    "user_id": video_info["data"]["View"]["owner"]["mid"],
}

st.table(video_data)

conn = st.connection("mysql", type="sql")
query = "SELECT * FROM video_static WHERE aid = :aid OR bvid = :bvid"
current = conn.query(
    query, params={"aid": video_data["aid"], "bvid": video_data["bvid"]}, ttl=0
)
if len(current) > 0:
    st.success("Video already exists in database.")
    st.table(current.T)
else:
    add_video = st.button("Add Video", key="add_video")

    if not add_video:
        st.stop()

    dbsession = conn.session
    dbsession.execute(
        text(
            "INSERT INTO video_static (aid, bvid, pubdate, title, description, tag, pic, type_id, user_id) "
            "VALUES (:aid, :bvid, :pubdate, :title, :description, :tag, :pic, :type_id, :user_id)"
        ),
        video_data,
    )
    dbsession.commit()

    current = conn.query(
        query, params={"aid": video_data["aid"], "bvid": video_data["bvid"]}, ttl=0
    )
    st.success("Video added successfully.")
    st.table(current.T)

    # Reset input fields by updating session state
    st.session_state.clear_form = True

    col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
    with col2:
        if st.button("Refresh now"):
            st.stop()
    with col1:
        with st.empty():
            for seconds in range(10):
                st.success(f"⏳ Page will refresh in {10 - seconds} seconds.")
                time.sleep(1)

    st.rerun()
