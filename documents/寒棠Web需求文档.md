# 寒棠 Web 需求文档

用户能够通过 HTTP Web 网页，添加一个寒棠收录的视频、修改一个视频的优先级、查询当前的任务列表、查询一个视频的基本信息和数据信息。

因为目前前后端开发均为 [去离子水](https://github.com/icedata-top/hantang-add/commits?author=Ovler-Young) 一人，故而对于接口的设计仅供参考。

## 1.合并AV号和BV号输入框 

AV号 判定方法：纯数字、AV（不区分大小写）开头+纯数字的为AV号。否则为BV号。
伪代码如下
```py
def handle_video_id(video_id: str) -> int:
    video_id = video_id.strip()

    if video_id.isdigit():
        return int(video_id)
    
    if (video_id.lower().startswith("av") and video_id[2:].isdigit()):
        return int(video_id[2:])
    
    return bvid_to_aid(video_id)
```

`bvid_to_aid()`参考网上开源代码。

### 2.表格内容有冗余

查询一个视频之后，会有两张表。我猜测一个是B站API现取的，另一个是`video_static`里的。但是很多情况下二者信息一致。可以删掉一个。

### 3.新增每日数据图表

目前的图表来自于`video_minute`。需要新增一张图表，反应每日数据`video_daily`。

### 4.新增收藏率图表

横着的矩形图（有点像进度条），我会发给你原型图。