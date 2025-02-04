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

可以只做增量的Growth，也就是做过一次差分的。

### 4.新增比率图表

横着的矩形图（有点像进度条），显示“超过收录范围内xx%”的视频，我会发给你原型图。

百分位数的实现方法：在每天凌晨统计一次，仅根据`video_daily`中的数据计算，然后插入到新的数据表。

### 5.优化前端

* 文本改成中文，或者能够中英文切换。
* 图表需要单位，比如Growth需要是每分钟/每秒。
* 默认不需要选中所有的字段，可以只选择播放量、收藏量、点赞量字段。

