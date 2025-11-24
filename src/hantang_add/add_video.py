import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit.components.v1 as components
from sqlalchemy import text
import requests
import re
import time
import math
import random
import secrets
from wbi import encWbi, getWbiKeys
from utils import word_level_diff


st.set_page_config(layout="wide")
st.header("添加视频")

if "clear_form" in st.session_state:
    st.session_state.video_id = ""
    del st.session_state.clear_form

video_id_input = st.text_input(
    "视频ID",
    placeholder="格式: BV号 (BVxxxxxxxxxx) / AV号 (av123456 or 123456) / URL",
    key="video_id",
    value=st.session_state.get("video_id", ""),
)

if not video_id_input:
    st.markdown("请输入有效的BV或AV号，输入后按回车键提交。")
    st.stop()

# Strip whitespace
video_id_input = video_id_input.strip()

# Determine if it's AV or BV ID
# Priority: Check for BV ID pattern first, then AV ID patterns
bv_match = re.search(r"BV[0-9a-zA-Z]{10}", video_id_input)

if bv_match:
    # BV ID detected
    video_id = bv_match.group(0)
    param_key = "bvid"
    player_id = f"bvid={video_id}"
elif video_id_input.isdigit():
    # Pure digits - AV ID
    video_id = video_id_input
    param_key = "aid"
    player_id = f"aid={video_id}"
elif video_id_input.lower().startswith("av") and video_id_input[2:].isdigit():
    # AV prefix + digits - AV ID
    video_id = video_id_input[2:]
    param_key = "aid"
    player_id = f"aid={video_id}"
else:
    st.warning("无效的视频ID，请输入有效的BV号或AV号。")
    st.stop()

components.iframe(f"https://player.bilibili.com/player.html?{player_id}", height=400)

# Update signed params based on ID type
img_key, sub_key = getWbiKeys()
signed_params = encWbi(params={param_key: video_id}, img_key=img_key, sub_key=sub_key)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}

# Generate random DedeUserID and DedeUserID__ckMd5
dede_user_id = math.floor(pow(random.random(), 4) * 1000000000000)
dede_user_id_ck_md5 = secrets.token_hex(8)

cookies = {
    "DedeUserID": str(dede_user_id),
    "DedeUserID__ckMd5": dede_user_id_ck_md5,
}

response = requests.get(
    "https://api.bilibili.com/x/web-interface/wbi/view/detail",
    params=signed_params,
    headers=headers,
    cookies=cookies,
)

video_info = response.json()

# display video title
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
    st.success("视频已存在于数据库中")

    # Preserve priority from existing record
    video_data["priority"] = current.iloc[0]["priority"]

    # Check for differences and build display table
    current_record = current.iloc[0]
    has_changes = False
    display_data = {}

    for field in video_data.keys():
        current_value = current_record[field]
        new_value = video_data[field]

        # Skip priority field in comparison
        if field == "priority":
            display_data[field] = str(current_value)
        elif current_value != new_value:
            has_changes = True
            # Show word-level diff for text fields
            display_data[field] = word_level_diff(current_value, new_value)
        else:
            # No change, show value normally
            display_data[field] = str(current_value)

    # Display table with diff formatting
    display_df = pd.DataFrame([display_data]).T
    display_df.columns = ["Value"]

    if has_changes:
        st.warning("检测到变更 - 正在自动更新...")
        st.markdown(display_df.to_markdown())

        # Automatically update the database
        dbsession = conn.session
        dbsession.execute(
            text(
                "UPDATE video_static SET bvid = :bvid, pubdate = :pubdate, title = :title, description = :description, tag = :tag, pic = :pic, type_id = :type_id, user_id = :user_id, priority = :priority WHERE aid = :aid"
            ),
            video_data,
        )
        dbsession.commit()
        st.success("视频数据更新成功！")
    else:
        st.info("视频数据已是最新")
        st.markdown(display_df.to_markdown())

else:
    st.write("新视频：")
    st.table(video_data)

if len(current) > 0:
    priority = current.iloc[0]["priority"]
    aid = current.iloc[0]["aid"]

    # Add priority change UI
    priority_options = {
        "不自动更新": None,
        "每分钟": 1,
        "每15分钟": 15,
        "每小时": 60,
    }

    new_priority = st.selectbox(
        "更改更新频率",
        options=list(priority_options.keys()),
        index=list(priority_options.values()).index(priority),
        help="自动检查视频更新的频率",
    )

    if new_priority and priority_options[new_priority] != priority:
        if st.button("更新优先级"):
            dbsession = conn.session
            dbsession.execute(
                text("UPDATE video_static SET priority = :priority WHERE aid = :aid"),
                {"priority": priority_options[new_priority], "aid": aid},
            )
            dbsession.commit()
            st.success("优先级更新成功！")
            time.sleep(1)
            st.rerun()

    # If priority is set, let user choose data source; otherwise default to Dynamic.
    if priority is not None:
        data_source = st.radio("选择数据源", options=["分钟", "每日汇总"])
        # Map Chinese to English for internal use
        data_source = "Minute" if data_source == "分钟" else "Dynamic"
    else:
        data_source = "Dynamic"

    # Fix min_date and max_date conversion
    min_date = pd.Timestamp.fromtimestamp(
        max(
            current.iloc[0]["pubdate"],
            (pd.Timestamp.now() - pd.Timedelta(days=3655)).timestamp(),
        )
    ).date()
    max_date = pd.Timestamp.now().date()
    start_date, end_date = st.date_input("选择日期范围", [min_date, max_date])

    if data_source == "Minute":
        query_data = "SELECT * FROM video_minute WHERE aid = :aid AND time BETWEEN :start_date AND :end_date ORDER BY time"
    else:
        # Limit rows to 3655 (e.g. near ten years of daily data)
        query_data = "SELECT * FROM video_daily WHERE aid = :aid AND record_date BETWEEN :start_date AND :end_date ORDER BY record_date"

    df = conn.query(
        query_data,
        params={"aid": aid, "start_date": start_date, "end_date": end_date},
        ttl=0,
    )

    # Process time column and rename table type based on data source
    table_type = data_source
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

        # Field names in Chinese
        field_names = {
            "view": "播放",
            "like": "点赞",
            "favorite": "收藏",
            "danmaku": "弹幕",
            "reply": "评论",
            "share": "分享",
        }

        # Add field selection checkboxes
        selected_fields = st.multiselect(
            "选择要显示的字段",
            options=list(field_names.keys()),
            default=["view", "like", "favorite"],
            format_func=lambda x: field_names[x],
        )

        # Filter plot_df based on selected fields
        if selected_fields:
            plot_df = plot_df[selected_fields]
        else:
            st.warning("请至少选择一个字段")
            st.stop()

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
                        name=field_names["view"],
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
                        name=field_names[col],
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
                        name=f"{field_names[col]} 原始",
                        marker=dict(
                            color=colors["view"],
                            size=2,  # 点的大小
                            opacity=0.8,  # 半透明
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
                        name=f"{field_names[col]} 增长",
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
                        marker=dict(color=colors[col], size=2, opacity=0.8),
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

        # Determine unit based on data source
        if table_type == "Minute":
            unit_text = "每分钟"
        else:
            unit_text = "每天"

        fig2.update_layout(
            title="增长量随时间变化",
            xaxis_title="日期/时间",
            yaxis_title=f"增长量 ({unit_text})",
            hovermode="x unified",
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        data_type_text = "分钟" if table_type == "Minute" else "每日"
        st.info(f"该视频暂无{data_type_text}数据。")

else:
    priority_options = {
        "每日": None,
        "每分钟": 1,
        "每15分钟": 15,
        "每小时": 60,
    }

    priority = st.selectbox(
        "更新频率",
        options=list(priority_options.keys()),
        index=0,
        help="自动检查视频更新的频率",
    )

    # Add priority to video_data dict:
    video_data["priority"] = priority_options[priority]

    add_video = st.button("添加视频", key="add_video")

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
    st.success("视频添加成功。")
    st.table(current.T)

    # Reset input fields by updating session state
    st.session_state.clear_form = True

    col1, col2 = st.columns([4, 1], vertical_alignment="bottom")
    with col2:
        if st.button("立即刷新"):
            st.stop()
    with col1:
        with st.empty():
            for seconds in range(10):
                st.success(f"⏳ 页面将在 {10 - seconds} 秒后刷新。")
                time.sleep(1)

    st.rerun()
