import streamlit as st
import requests
import re
from wbi import encWbi, getWbiKeys

st.header("Add Video")

col1, col2 = st.columns(2)

with col1:
    bv_id = st.text_input("Video BV ID", placeholder="format: BV[0-9a-zA-Z]{10}", value="")

with col2:
    av_id = st.text_input("Video AV ID", placeholder="format: [0-9]+ / av[0-9]+", value="")

if not bv_id and not av_id:
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

st.write(
    f'<iframe src="//player.bilibili.com/player.html?{player_id}" scrolling="no" border="0" frameborder="no" framespacing="0" allowfullscreen="true" style="width:100%;height:500px"> </iframe>',
    unsafe_allow_html=True,
)

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

add_video = st.button("Add Video", key="add_video")

if add_video:
    conn = st.connection("mysql", type="sql")

    query = "SELECT * FROM video_static WHERE aid = '{}' OR bvid = '{}'".format(
        video_data["aid"], video_data["bvid"]
    )

    current = conn.query(query, ttl=0)

    if len(current) == 0:
        query_str = "INSERT INTO video_static (aid, bvid, pubdate, title, description, tag, pic, type_id, user_id) VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(
            video_data["aid"],
            video_data["bvid"],
            video_data["pubdate"],
            video_data["title"],
            video_data["description"],
            video_data["tag"],
            video_data["pic"],
            video_data["type_id"],
            video_data["user_id"],
        )

        insert = conn.query(query_str)

        st.success("Video inserted.")

        # Test if the video is in db
        current = conn.query(query, ttl=0)
        st.success("Video added successfully.")
    else:
        st.success("Video already exists in database.")

    st.table(current.T)
