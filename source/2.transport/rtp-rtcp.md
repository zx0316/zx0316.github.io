# RTP / RTCP 与 NACK 重传

```{note}
本篇施工中。先把骨架和关键问题列出来，后续填充。
```

## 要解决的核心问题

RTP 只做一件事：**给每个媒体包一个序号和时间戳**，让接收端能还原顺序和节奏。
RTCP 则负责把「收得怎么样」反馈回发送端。

## 报文结构速览

```{todo}
RTP 固定头 12 字节逐字段拆解（V/P/X/CC/M/PT/seq/timestamp/SSRC）
```

```{todo}
RTCP SR / RR / SDES / BYE 的用途区分
```

```{todo}
NACK 与 PLI / FIR 的区别：丢包重传 vs 关键帧请求
```

## 为什么 WebRTC 不用 TCP 重传

TCP 的重传是「传输层无条件等待」，代价是队头阻塞。
WebRTC 的重传是「应用层有条件重传」——只在 Jitter Buffer 还来得及的时候才 NACK。

```{warning}
NACK 不是越多越好。重传包本身也占带宽，网络已经拥塞时再发 NACK 会雪上加霜。
```

## 参考

- {doc}`../3.qos/index` — 弱网对抗的整体策略
