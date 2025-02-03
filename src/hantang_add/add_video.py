import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit.components.v1 as components
from sqlalchemy import text
import requests
import re
import time
from wbi import encWbi, getWbiKeys

st.set_page_config(layout="wide")
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
    "pic": video_info["data"]["View"]["pic"],
    "type_id": video_info["data"]["View"]["tid"],
    "user_id": video_info["data"]["View"]["owner"]["mid"],
}

conn = st.connection("mysql", type="sql")
query = "SELECT * FROM video_static WHERE aid = :aid OR bvid = :bvid"
current = conn.query(
    query, params={"aid": video_data["aid"], "bvid": video_data["bvid"]}, ttl=0
)
if len(current) > 0:
    st.success("Video already exists in database:")
    df_video_data = pd.DataFrame([video_data])
    df_video_data["priority"] = current.iloc[0]["priority"]
    comparison = pd.concat([current.iloc[0], df_video_data.iloc[0]], axis=1)
    comparison.columns = ['Current', 'New']
    st.table(comparison)
    # if different, update the video data after asking
    if not comparison["Current"].equals(comparison["New"]):
        st.warning("Video data is different from the current record.")
        st.markdown("Click the button below to update the video data.")
        different_fields = comparison[comparison["Current"] != comparison["New"]].index
        st.write("Different fields:")
        st.write(different_fields)
        if st.button("Update Video Data"):
            video_data["priority"] = current.iloc[0]["priority"]
            dbsession = conn.session
            dbsession.execute(
                text(
                    "UPDATE video_static SET bvid = :bvid, pubdate = :pubdate, title = :title, description = :description, tag = :tag, pic = :pic, type_id = :type_id, user_id = :user_id, priority = :priority WHERE aid = :aid"
                ),
                video_data,
            )
            dbsession.commit()
            st.success("Video data fixed successfully!")
            time.sleep(10)
            st.rerun()
else:
    st.write("New Video:")
    st.table(video_data)

if len(current) > 0:
    priority = current.iloc[0]["priority"]
    aid = current.iloc[0]["aid"]

    # Add priority change UI
    priority_options = {
        "N/A": None,
        "Every minute": 1,
        "Every 15 minutes": 15,
        "Every hour": 60,
    }

    new_priority = st.selectbox(
        "Change update frequency",
        options=list(priority_options.keys()),
        index=list(priority_options.values()).index(priority),
        help="How often to automatically check for video updates",
    )

    if new_priority and priority_options[new_priority] != priority:
        if st.button("Update Priority"):
            dbsession = conn.session
            dbsession.execute(
                text("UPDATE video_static SET priority = :priority WHERE aid = :aid"),
                {"priority": priority_options[new_priority], "aid": aid},
            )
            dbsession.commit()
            st.success("Priority updated successfully!")
            time.sleep(1)
            st.rerun()

    if priority is not None:
        query = "SELECT * FROM video_minute WHERE aid = :aid ORDER BY time LIMIT 1000"
        table_type = "Minute"
    else:
        query = "SELECT * FROM video_dynamic WHERE aid = :aid ORDER BY record_date LIMIT 1000"
        table_type = "Dynamic"

    df = conn.query(query, params={"aid": aid}, ttl=0)

    if not df.empty:
        # Convert timestamp/date to datetime
        if table_type == "Minute":
            df["datetime"] = pd.to_datetime(df["time"], unit="s")
            # Remove points that are <30s from the last data point
            df = df.sort_values("datetime")
            kept = []
            last = None
            for i, row in df.iterrows():
                if last is None or (row["datetime"] - last).total_seconds() >= 20:
                    kept.append(i)
                    last = row["datetime"]
            df = df.loc[kept]
        else:
            df["datetime"] = pd.to_datetime(df["record_date"])

        # Prepare data for plotting
        plot_columns = [
            "datetime",
            "favorite",
            "danmaku",
            "reply",
            "share",
            "like",
            "view",
        ]
        plot_df = df[plot_columns].set_index("datetime")

        if table_type == "Minute":
            time_diff = plot_df.index.to_series().diff().dt.total_seconds().div(60)
        else:
            time_diff = plot_df.index.to_series().diff().dt.days

        time_diff = time_diff.bfill()        
        # Create Plotly figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        colors = {
            "favorite": "#1f77b4",
            "danmaku": "#ff7f0e",
            "reply": "#2ca02c",
            "share": "#d62728",
            "like": "#9467bd",
            "view": "#8c564b",
        }

        for col in plot_df.columns:
            if col == "view":
                fig.add_trace(
                    go.Scatter(
                        x=plot_df.index,
                        y=plot_df["view"],
                        name="view",
                        line=dict(color=colors["view"], shape="spline"),
                        mode="lines",
                    ),
                    secondary_y=True,
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=plot_df.index,
                        y=plot_df[col],
                        name=col,
                        line=dict(color=colors[col], shape="spline"),
                        mode="lines",
                    ),
                    secondary_y=False,
                )

        fig.update_yaxes(rangemode="tozero", secondary_y=False)
        fig.update_yaxes(rangemode="tozero", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        # Create new figure for growth (derivative) lines
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])

        # Initialize variables to track max and min values for both axes
        current_max = -float("inf")
        current_min = float("inf")
        view_max = -float("inf")
        view_min = float("inf")

        for col in plot_df.columns:
            diff = plot_df[col].diff().fillna(0)
            rate = diff / time_diff.replace(0, 1)
            if table_type == "Minute":
                ma = rate.rolling(window=6, min_periods=1).quantile(0.5).interpolate()
            else:
                ma = rate
            if col == "view":
                fig2.add_trace(
                    go.Scatter(
                        x=plot_df.index,
                        y=rate,
                        name=f"{col} raw",
                        marker=dict(
                            color=colors["view"], 
                            size=2,  # 点的大小
                            opacity=0.8  # 半透明
                        ),
                        mode="markers",
                    ),
                    secondary_y=True,
                )
                # 添加平滑曲线（保持原有代码）
                fig2.add_trace(
                    go.Scatter(
                        x=plot_df.index,
                        y=ma,
                        name=f"{col} growth",
                        line=dict(color=colors["view"]),
                        mode="lines",
                    ),
                    secondary_y=True,
                )
                # Update view axis ranges based on MA values
                view_max = max(view_max, ma.max())
                view_min = min(view_min, ma.min())
            else:
                fig2.add_trace(
                    go.Scatter(
                        x=plot_df.index,
                        y=rate,
                        name=f"{col} raw",
                        marker=dict(
                            color=colors[col], 
                            size=2,
                            opacity=0.8
                        ),
                        mode="markers",
                    ),
                    secondary_y=False,
                )
                # 添加平滑曲线（保持原有代码）
                fig2.add_trace(
                    go.Scatter(
                        x=plot_df.index,
                        y=ma,
                        name=f"{col} growth",
                        line=dict(color=colors[col]),
                        mode="lines",
                    ),
                    secondary_y=False,
                )
                # Update primary axis ranges based on MA values
                current_max = max(current_max, ma.max())
                current_min = min(current_min, ma.min())

        # Update y-axis ranges considering both datasets
        fig2.update_yaxes(
            range=[min(current_min, view_min / 10), max(current_max, view_max / 10)],
            secondary_y=False,
        )
        fig2.update_yaxes(
            range=[min(current_min * 10, view_min), max(current_max * 10, view_max)],
            secondary_y=True,
        )

        fig2.update_layout(
            title="Growth (Derivative) Over Time",
            xaxis_title="Date/Time",
            yaxis_title="Growth",
            hovermode="x unified",
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info(f"No {table_type.lower()} data available for this video yet.")

else:
    priority_options = {
        "N/A": None,
        "Every minute": 1,
        "Every 15 minutes": 15,
        "Every hour": 60,
    }

    priority = st.selectbox(
        "Update frequency",
        options=list(priority_options.keys()),
        index=0,
        help="How often to automatically check for video updates",
    )

    # Add priority to video_data dict:
    video_data["priority"] = priority_options[priority]

    add_video = st.button("Add Video", key="add_video")

    if not add_video:
        st.stop()

    dbsession = conn.session
    dbsession.execute(
        text(
            "INSERT INTO video_static (aid, bvid, pubdate, title, description, tag, pic, type_id, user_id, priority) "
            "VALUES (:aid, :bvid, :pubdate, :title, :description, :tag, :pic, :type_id, :user_id, :priority)"
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
