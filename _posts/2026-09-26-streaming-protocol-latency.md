---
title: "开篇：RTMP、HLS 与 WebRTC，直播延迟差距到底在哪？"
date: 2026-09-26 20:00:00 +0800
categories: [流媒体]
tags: [WebRTC, RTMP, HLS, 低延迟直播, 协议对比]
---

## 为什么从"延迟"聊起

做流媒体的第一个灵魂拷问往往是：**为什么同样是直播，HLS 能慢半分钟，WebRTC 却能做到视频聊天级别的实时互动？**

答案藏在协议的设计目标里。本文作为博客开篇，先用一张表建立直觉，后续文章再逐一拆开 RTP、GCC、Jitter Buffer 这些硬骨头。

## 常见传输协议延迟对比

| 协议/方案 | 典型延迟 | 传输层 | 典型场景 |
| :--- | :--- | :--- | :--- |
| HLS（普通分片） | 5 ~ 30 s | HTTP/TCP | 大规模 CDN 分发、点播式直播 |
| LL-HLS | 1 ~ 3 s | HTTP/TCP | 对延迟有要求的直播分发 |
| RTMP / RTMPS | 1 ~ 5 s | TCP | 推流、传统直播拉流 |
| SRT | 0.5 ~ 3 s | UDP | 跨主播传、弱网传输 |
| **WebRTC** | **< 500 ms** | **UDP/SRTP** | 视频通话、连麦、云游戏 |

> 延迟数值是经验范围，实际还受 GOP、缓冲区策略、网络抖动影响，不要拿来当 SLA。
{: .prompt-warning }

## 延迟差距的三个主要来源

### 1. 分片（Chunk）大小

HLS 本质是"边录边播的小文件"。一个 TS/fMP4 分片通常 2~10 秒，播放器至少要缓冲 3 个分片——天然就是十几秒起步。LL-HLS 靠的是把分片再切成 Partial Segment（200ms 左右）才把延迟压下来。

### 2. TCP 的队头阻塞

RTMP 跑在 TCP 上，丢一个包，后面的音视频数据都得等重传。实时场景里，"旧于当前时刻的数据"其实已经没有价值——WebRTC 选择 UDP，宁可丢帧也不等待，把取舍权交给应用层的 NACK / FEC。

### 3. 播放器抖动缓冲（Jitter Buffer）

接收端缓存越多，画面越平滑，但延迟越大。WebRTC 的 Jitter Buffer 会根据网络抖动**动态伸缩**，在"流畅"和"实时"之间持续找平衡。

## 用代码感受一下"延迟预算"

以 30fps 为例，一帧的采集间隔只有约 33ms。端到端 300ms 的预算大致这样分配：

```cpp
#include <cstdint>
#include <cstdio>

// 毫秒为单位的端到端延迟预算（示例模型，非真实测量）
struct LatencyBudget {
    int capture_encode_ms = 30;   // 采集 + 编码
    int network_ms        = 80;   // 上行 + SFU 转发 + 下行
    int jitter_buffer_ms  = 120;  // 接收端抖动缓冲
    int decode_render_ms  = 30;   // 解码 + 渲染
};

int main() {
    LatencyBudget b;
    int total = b.capture_encode_ms + b.network_ms
              + b.jitter_buffer_ms + b.decode_render_ms;
    std::printf("端到端延迟预算: %d ms\n", total);  // 260 ms
    return 0;
}
```

> WebRTC 的低延迟不是单点魔法，而是采集、编码、传输、缓冲、解码全链路一起抠毫秒的结果。
{: .prompt-tip }

## 后续计划

接下来会围绕 WebRTC 源码与工程实践展开，先给自己挖几个坑：

1. RTP / RTCP 协议结构与 NACK 重传机制
2. GCC 带宽估计：基于延迟与基于丢包的两条控制回路
3. Pacer 发包 pacing 与突发流量抑制
4. 从零实现一个最小 WebRTC 推拉流 Demo（C++）

欢迎通过侧边栏的 GitHub 或邮件与我交流。
