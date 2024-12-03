# hantang-add

## 配置

创建 `.streamlit/secrets.toml` 文件，添加如下内容：

```toml
[connections.mysql]
dialect = "mysql"
driver = "pymysql"
host = "localhost"
port = 3306
database = "xxx"
username = "xxx"
password = "xxx"
```

## 安装

前置需求：安装pdm。 [文档](https://pdm-project.org/zh-cn/latest/#_3) [en](https://pdm-project.org/en/latest/#_3)

```shell
pdm install
```

## 运行

在对的venv里，运行：

```shell
streamlit run app.py
```
