# - FROM：指定基础镜像；
# - python:3.12：官方 Python 3.12；
# - -slim：精简版，去掉了文档、编译器等，体积小很多；
# - 为什么不从零开始装 Python：官方镜像已经处理好依赖，稳定又省事。
# 能得到什么：一个干净、体积可控的 Python 运行环境。
FROM python:3.12-slim

# - 容器内的默认工作目录；
# - 后面所有 COPY、RUN 都相对它执行；
# - 不存在会自动创建。
# 为什么需要：避免文件散落在根目录，路径可控。
WORKDIR /app

# - PYTHONDONTWRITEBYTECODE=1：不生成 __pycache__，镜像更干净；
# - PYTHONUNBUFFERED=1：日志立即输出，docker logs 能实时看到，不会卡在缓冲区。
# 能得到什么：干净的镜像 + 可实时观察的日志。
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# - 把依赖清单复制进镜像；
# - 只复制这一个文件，不复制其他代码。
# 为什么先复制它：Docker 是分层构建，这一层只有依赖清单变化时才重建。代码改动不会导致重新安装依赖，构建速度大幅提升。
COPY requirements-app.txt .


# - RUN：构建镜像时执行；
# - --no-cache-dir：不保存 pip 下载缓存，镜像更小；
# - -r requirements-app.txt：按清单安装；
# - -i 清华源：国内构建更快。
# 能得到什么：依赖被固化进镜像，运行时无需联网安装。
RUN pip install --no-cache-dir -r requirements-app.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple


# - 把业务代码复制进镜像；
# - 放在依赖安装之后：代码频繁改，依赖不常改，这样依赖层可以复用缓存。
# 能得到什么：最小构建：只复制真正需要运行的文件。
COPY app.py .


# - 声明容器会监听 8000 端口；
# - 这是文档性声明，真正映射端口靠 docker run -p。
# 能得到什么：使用者知道该映射哪个端口。
EXPOSE 8000

# - CMD：容器启动时执行的命令；
# - app:app：模块 app.py 里的 app 实例；
# - --host 0.0.0.0：关键——必须监听所有网卡，否则容器外访问不到；
# - --port 8000：监听端口。
# 为什么必须是 0.0.0.0：默认 127.0.0.1 只允许容器内部访问，宿主机映射端口也进不来。
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

