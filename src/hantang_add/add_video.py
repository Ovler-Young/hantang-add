import streamlit as st
import requests

# Initialize connection.
conn = st.connection("mysql", type="sql")

st.header("Add Video")

# input video bv_id
bv_id = st.text_input("Video BV ID")

st.button("Add Video", key="add_video")

video_info = requests.get(
    f"https://api.bilibili.com/x/web-interface/view?bvid={bv_id}"
).json()

# display video info

st.json(video_info)

# Check if the video is in db

current = conn.query(
    "SELECT * FROM video_static WHERE bvid = %s", (st.session_state.bv_id,)
)

if current:
    st.write("Video already exists in database.")
else:
    # try aid
    aid = video_info["data"]["aid"]
    current_aid = conn.query("SELECT * FROM video_static WHERE aid = %s", (aid,))
    if current_aid:
        st.write("Video already exists in database.")
    else:
        add = conn.query(
            "INSERT INTO video_static (aid, bvid, pubdate, title, description, tag, pic, type_id, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                video_info["data"]["aid"],
                video_info["data"]["bvid"],
                video_info["data"]["pubdate"],
                video_info["data"]["title"],
                video_info["data"]["desc"],
                "", # todo
                video_info["data"]["pic"],
                video_info["data"]["tid"],
                video_info["data"]["owner"]["mid"],
            ),
        )
