# hantang-add

## 数据库连接信息

``` toml
[connections.mysql]
dialect = "mysql"
driver = "pymysql"
host = "your_host"
port = 3306
database = "your_database"
username = "your_username"
password = "your_password"
```

## 云上运行

1. 前往 [streamlit.io](https://share.streamlit.io/deploy)，进行部署（可能需要注册其账号）。

   仓库是 `icedata-top/hantang-add`

   注意 `Main file path` 为 `src\hantang-add\add_video.py`

   可以自己修改App Url，默认是不公开的。

2. 点击Advanced settings，确认Python 版本为3.12，在下方的secrets中填入数据库连接信息，并点击 `Save` 保存。

3. 点击 `Deploy`，等待部署完成。

## 本地运行


1. 前置需求：安装pdm。 [文档](https://pdm-project.org/zh-cn/latest/#_3) [en](https://pdm-project.org/en/latest/#_3) 紧接着，安装依赖：

    ```shell
    pdm install
    ```

    你也可以选择使用别的依赖管理工具，如pipenv、poetry等。需要的包已经导出到了`requirements.txt`。

2. 在 `.streamlit/secrets.toml` 中填入数据库连接信息。

3. 在对的venv里，运行：

    ```shell
    streamlit run app.py
    ```

    它会自动打开浏览器，访问 `http://localhost:8501`。
