import streamlit as st
import requests
from wbi import encWbi, getWbiKeys

st.header("Add Video")

# input video bv_id
bv_id = st.text_input("Video BV ID")

st.write(
    f'<iframe src="//player.bilibili.com/player.html?bvid={bv_id}" scrolling="no" border="0" frameborder="no" framespacing="0" allowfullscreen="true" style="width:100%;height:500px"> </iframe>',
    unsafe_allow_html=True,
)


# Get wbi keys
img_key, sub_key = getWbiKeys()
# sign params
signed_params = encWbi(params={"bvid": bv_id}, img_key=img_key, sub_key=sub_key)
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
