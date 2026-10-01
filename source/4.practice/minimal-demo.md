# 从零实现一个最小 WebRTC 推拉流 Demo

```{note}
本篇施工中。
```

## 目标

不依赖 libwebrtc 全家桶，先跑通一条最小链路：

```{mermaid}
flowchart LR
    A[采集] --> B[编码]
    B --> C[RTP 打包]
    C --> D[UDP 发送]
    D --> E[Jitter Buffer]
    E --> F[解码]
    F --> G[渲染]
```

## 分步拆解

```{todo}
用 PeerConnection 建立连接：SDP offer / answer 交换
```

```{todo}
拿到本地媒体流并渲染到页面
```

```{todo}
用 getStats() 观察端到端延迟、丢包、码率
```

```{todo}
换成自己实现的 RTP 发送，验证协议理解是否正确
```

```{tip}
先用浏览器 API 跑通，再下探到 C++ 层。反过来做会被一堆信令细节劝退。
```
