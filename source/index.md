# 流媒体技术笔记

::: {admonition} 关于本站
:class: note

一份围绕 **WebRTC / 低延迟直播 / 音视频工程** 的学习笔记，记录协议原理、源码阅读与工程实践。
内容以「能讲清楚一件事」为目标，而不是 API 手册的搬运。
:::

## 这本笔记想解决什么

做流媒体最容易卡住的地方，往往是「知道名词，说不清机制」：

- 为什么 HLS 慢半分钟，WebRTC 却能做到几百毫秒？
- 丢包了到底该等重传，还是直接丢帧？
- 带宽估计到底在估计什么，GCC 的两条控制回路怎么配合？

所以这份笔记按 **问题域** 组织，而不是按时间线组织。每一章都可以单独读，
章节之间用交叉链接串起来。

## 阅读路线

```{toctree}
:maxdepth: 2
:caption: 目录
:numbered:

1.latency/index
2.transport/index
3.qos/index
4.practice/index
```

## 快速参考

| 主题 | 一句话结论 |
| :--- | :--- |
| 延迟量级 | HLS 5~30s、RTMP 1~5s、SRT 0.5~3s、WebRTC &lt; 500ms |
| 传输层选择 | 要实时就上 UDP，要兼容就吃 CDN 的 HTTP 红利 |
| 抗弱网 | NACK / FEC / Jitter Buffer 三件套，按场景配比 |
| 带宽估计 | 基于延迟的回路定上限，基于丢包的回路做兜底 |

## 相关链接

- [GitHub: zx0316](https://github.com/zx0316)
- 邮箱：lizhixiao0316 [at] 163.com

```{tip}
右侧 / 左侧的目录树可以随时跳转。页面右上角有搜索框，直接搜关键词更快。
```
