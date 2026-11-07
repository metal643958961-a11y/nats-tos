# NATS Server for TOS 7 · 2.15.2.1 Beta

本机应用通过 NATS 主题发送消息、向队列工作进程发出请求，并通过 JetStream 保存和重放消息。无 Web UI。仅支持 TOS 7 x86_64、Docker Engine 及 Compose；单节点，无需外部数据库。

在应用实际 Compose 项目目录（docker-compose.yml 所在目录）准备以下文件后启动。命令假设首次安装、具备在项目目录设置权限的管理权限；已有 .env 请保留并编辑，不要覆盖。
  
~~~sh
(umask 077; set -C; printf 'NATS_CLIENT_SECRET=%s\n' "$(openssl rand -hex 32)" > .env)
install -d -m 0700 -o 1000 -g 1000 data
~~~

将 .env 中的随机值交给受信任的本机客户端，用户名 client，地址 127.0.0.1:14222。无默认密码。不要公开 .env、Compose 展开结果或容器完整 inspect 输出：Docker 管理员可看到启动参数。此适配面向单一信任域；同账号的客户端共享主题与 JetStream 权限。不提供远程 TLS、管理网页或匿名监控端口。容器从 Docker Hub 拉取约 7.3 MB 压缩镜像，以 UID 1000 运行，根文件系统只读，data 为唯一持久化挂载。为每个 JetStream 流设置 max_bytes/保留策略，定期备份 data 和 .env；删除 data 会丢失保存的消息。普通 Core NATS 发布不自动持久化。

构建：python3 build.py（需要系统 Ruby/Psych）；在 dist 内核验 SHA256SUMS。安装包根部仅含四份适配文件。原始固定镜像、应用源码与许可证分别见 [Docker Hub](https://hub.docker.com/_/nats)、[NATS Server v2.15.2](https://github.com/nats-io/nats-server/tree/v2.15.2) 和 [Apache-2.0 全文](licenses/NATS-Apache-2.0.txt)。安装包不包含服务器二进制或镜像层，图标为本适配自绘。功能测试脚本仅用于授权的专用 Linux Docker 机器，需事先具备锁定镜像，端口 14222 和容器名 nats 必须空闲。

本版经 TOS 7.0.1422 真机以原样 Compose 离线验收；演示机默认代理冷拉取返回 502。应用中心安装、项目 .env 的部署时机及卸载数据选项尚未验证。
