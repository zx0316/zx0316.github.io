# 三 · QoS 与弱网对抗篇

网络不会一直好。这一篇讲「网络变差时，系统该牺牲什么」。

```{toctree}
:maxdepth: 2

gcc
jitter-buffer
```

## 三件套的分工

| 手段 | 对抗的问题 | 代价 |
| :--- | :--- | :--- |
| NACK | 随机丢包 | 引入一个 RTT 的等待 |
| FEC | 连续丢包、来不及重传 | 固定冗余带宽 |
| Jitter Buffer | 抖动、乱序 | 增加延迟 |

```{todo}
自适应码率（ABC）与 simulcast / SVC 的取舍
```
