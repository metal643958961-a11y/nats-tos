# NATS Server v2.15.2.1 Beta

TOS 7 x86_64 Docker 应用，ID nats。单节点 NATS Server v2.15.2 提供主题路由、队列组、请求应答及 JetStream 消息持久化。无 Web 界面。依赖 Docker Engine。首次启动须按 README 准备项目 .env 和 data 目录；仅监听宿主回环地址 127.0.0.1:14222。

经本地与 TOS 7.0.1422 真机离线 Compose 验证，错误口令被拒绝，请求应答正常，容器重建后读回同一条消息。演示机从 Docker Hub 冷拉取时默认代理返回 502；应用中心一键安装、首次设置及卸载尚未验证。

附件 nats.tar.gz 的 SHA256：f691be9fc1fac900a4342532491b6247af30c7560b91eba049dfd638afdc511d。上游许可证 Apache-2.0；包中不包含镜像层。[反馈](https://github.com/metal643958961-a11y/nats-tos/issues)
