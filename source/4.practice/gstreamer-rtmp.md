# 用 GStreamer 实现 RTMP 推流：流程拆解与性能优化难点

> 分类：工程实践 · 标签：GStreamer / RTMP / 推流 / 性能优化

## 为什么值得单独写一篇

RTMP 虽然是「老协议」，但到今天依然是**推流端的事实标准**——OBS、各大直播平台的采集端、大量嵌入式设备（安防摄像头、机顶盒）都在用 RTMP ingest。而 GStreamer 是这类场景最常见的实现载体：管线化建模天然适合「采集 → 编码 → 封装 → 发送」这条链路，插件生态覆盖软编硬编、各种采集源。

但「能跑通 `gst-launch` 一条命令」和「在生产环境里稳定推 7×24 小时」中间隔着一堆坑：编码器选型、队列背压、音视频交错、断线重连。这篇就把整条链路拆开讲。

```{note}
前置阅读：[延迟篇](../1.latency/protocol-latency.md) 里已经讲过 RTMP 走 TCP 带来的队头阻塞问题，本文聚焦**发送端**的实现与调优，不再重复协议层分析。
```

## 一、最小可用管线

先看一条能直接跑的命令：

```{code-block} bash
:caption: 最小 RTMP 推流管线
:linenos:

gst-launch-1.0 \
  v4l2src device=/dev/video0 ! \
  video/x-raw,width=1280,height=720,framerate=30/1 ! \
  videoconvert ! x264enc tune=zerolatency bitrate=2500 key-int-max=60 ! \
  h264parse config-interval=-1 ! \
  flvmux streamable=true name=mux ! \
  rtmp2sink sync=false location="rtmp://server/live/streamkey" \
  pulsesrc ! audioconvert ! audioresample ! \
  avenc_aac bitrate=128000 ! aacparse ! mux.
```

拆开看每个组件的职责：

| 组件 | 职责 | 关键点 |
| :--- | :--- | :--- |
| `v4l2src` / `pulsesrc` | 采集源 | 尽量在源上就锁定分辨率/帧率，避免下游缩放 |
| `videoconvert` | 色彩空间转换 | 编码器吃 yuv420p，摄像头常给 yuyv，必须转 |
| `x264enc` | H.264 软编 | `tune=zerolatency` 关 B 帧、关 lookahead |
| `h264parse` | 码流规范化 | 补全 SPS/PPS、把 codec_data 塞进 caps |
| `avenc_aac` | AAC 编码 | FLV 标准音频只认 AAC（MP3 是历史包袱） |
| `flvmux` | FLV 封装 | `streamable=true` 边封边发，不写文件尾 |
| `rtmp2sink` | RTMP 发送 | 原生 RTMP 实现，不依赖老掉牙的 librtmp |

```{tip}
`rtmpsink`（基于 librtmp）和 `rtmp2sink`（gst-plugins-bad 里的独立重写版）名字只差一个 2。新项目一律用 `rtmp2sink`：librtmp 那套代码早已无人维护，且在断流时的行为不可控。
```

## 二、数据流全链路

一条推流管线在 GStreamer 内部的完整数据路径是这样：

```{mermaid}
flowchart LR
    A[v4l2src<br/>采集] --> B[videoconvert<br/>色彩转换]
    B --> C[x264enc<br/>H.264 编码]
    C --> D[h264parse<br/>码流规范化]
    E[pulsesrc<br/>音频采集] --> F[avenc_aac<br/>AAC 编码]
    D --> G[flvmux<br/>FLV 封装]
    F --> G
    G --> H[rtmp2sink<br/>RTMP 发送]
    H --> I((CDN / 流媒体服务器))
```

### 2.1 能力协商：FLV 只认特定编码

GStreamer 的 caps 协商会自上而下传递约束。这里的关键约束来自 `flvmux`：FLV 容器标准只支持 **H.264 + AAC** 这一对组合（Sorenson H.263 和 MP3 属于历史遗留）。这意味着：

- 摄像头出的是 **VP8**？对不起，FLV 装不下，必须先转码成 H.264
- 想推 **H.265**？标准 FLV 不支持（Enhanced-RTMP 扩展是后来的事，服务器端还得配合）

### 2.2 时间戳：DTS 才是 FLV 的节拍

- 采集源按 pipeline 时钟给 buffer 打 **PTS**
- 编码器输出 **DTS**：开了 B 帧后 DTS ≠ PTS，需要重排
- `flvmux` 按 **DTS** 排序写 FLV tag

这就是为什么低延迟场景一律 `tune=zerolatency`（禁 B 帧）：B 帧引入编码端重排缓冲，DTS/PTS 错位，还会白白增加 1~2 帧延迟。RTMP 推流场景里 B 帧几乎从来不是好买卖。

### 2.3 codec_data 与「晚加入观众」问题

FLV 里 H.264 的 SPS/PPS 不是存在码流里，而是放在 **AVC sequence header**（由 caps 里的 `codec_data` 字段携带）。两个后果：

1. `h264parse` 必须在 mux 之前，把 SPS/PPS 从码流里解析出来塞进 caps
2. 观众中途加入时，服务器从任意位置开始拉流——如果码流里没有周期性内嵌 SPS/PPS，解码器永远初始化不出来，黑屏到下一个关键帧

所以 `config-interval=-1` 是**必配项**：让 h264parse 在每个 IDR 前重新插入 SPS/PPS。配合 2 秒 GOP（`key-int-max=60` @ 30fps），观众最多 2 秒出图。

### 2.4 发送端握手流程

`rtmp2sink` 连上服务器后会走完 RTMP 的固定套路：

```
握手（C0/C1/C2 ↔ S0/S1/S2）
  → connect（建 RTMP 连接）
  → createStream（拿 stream id）
  → publish（声明推流模式）
  → 发送 AVC sequence header + AAC AudioSpecificConfig
  → 持续发送音视频 FLV tag
```

了解这个流程的价值在排查：**「连上了但没画面」大概率卡在 sequence header 之前**——往往是音频分支没出数据，`flvmux` 在等两边凑齐封装头（见 4.3 节）。

## 三、关键配置速查

| 参数 | 推荐值 | 原因 |
| :--- | :--- | :--- |
| `key-int-max` | 2 × 帧率 | 2 秒 GOP：晚加入快出图，CDN 切片友好 |
| `tune=zerolatency` | 必开 | 禁 B 帧/lookahead，延迟换轻微画质损失 |
| `speed-preset` | `veryfast` 或 `superfast` | 再慢实时性就保不住了 |
| `vbv-bufsize` | ≈ bitrate | 限制码率突发，防上游队列瞬间积压 |
| `h264parse config-interval` | `-1` | 每 IDR 插 SPS/PPS，晚加入观众秒出图 |
| `flvmux streamable` | `true` | 直播没有文件尾，不写 duration |
| `rtmp2sink sync` | `false` | 不按时钟节拍发送，积压时快速冲掉 |
| `queue leaky` | `downstream`（采集分支） | 队满丢老帧，延迟不累积 |

## 四、性能优化难点（重点）

### 4.1 编码器：软编的上限与硬编的坑

**软编 `x264enc`** 的上限好估算：1280×720@30、`veryfast` 档大约吃掉 1~2 个现代 CPU 核心；到 1080p60 就很勉强了。CPU 打满的连锁反应比「卡」更糟——编码一帧的耗时超过帧间隔，上游队列开始积压，**延迟持续增长且不可逆**。

**硬编**（`nvh264enc` / `qsvh264enc` / `vah264enc`）省 CPU，但各有各的坑：

- **色彩范围不匹配**：摄像头出 full range，硬编按 limited range 处理，画面整体发灰。 caps 里显式声明 `colorimetry` 是唯一解
- **force-keyframe 支持参差**：软编对 `GstForceKeyUnit` 事件响应可靠，部分硬编插件对 IDR 间隔的控制要靠自己的属性（如 `nvh264enc` 的 `gop-size`），跨插件行为不一致
- **驱动差异**：嵌入式平台（Rockchip/Amlogic）的硬编插件质量参差，有时「看起来能跑」但长时间推流会有内存泄漏或时间戳漂移

```{warning}
选硬编之前先做 24 小时长跑测试，盯两件事：RSS 内存曲线是否平稳、DTS 是否单调递增。这两条不过关，一切优化免谈。
```

### 4.2 队列与背压：延迟和丢帧的两难

GStreamer 的 `queue` 默认**无界**（实际有巨大的默认上限）。网络一抖，`rtmp2sink` 发送变慢 → 背压传回 `flvmux` → 编码队列膨胀 → 延迟越攒越多，画面越来越「回顾历史」。直播里旧数据没有价值，所以必须主动丢：

```{code-block} text
:caption: 有界的、会丢帧的队列

queue max-size-time=3000000000 max-size-bytes=0 max-size-buffers=0 leaky=downstream
```

- `max-size-time=3s`：队列里最多攒 3 秒数据
- `leaky=downstream`：队满时丢队头的老数据，新数据永远进得来

这背后是一个基本原则：**直播推流端永远该「丢过去、保现在」**，和 WebRTC 的 NACK 取舍逻辑（见 [QoS 篇](../3.qos/index.md)）在哲学上是一致的——只是 RTMP 没有协议层的丢帧机制，只能在管线里自己动手。

### 4.3 音视频同步与 mux 交错

`flvmux` 要等**所有已连接的分支**都给出编码配置（codec_data）才能写 FLV 头，之后按 DTS 交错音视频 tag。这带来两个经典故障：

1. **推流已连接，服务器收不到任何数据** —— 十有八九是音频分支挂了（设备被占用、权限问题），mux 在等音频的配置信息。排查方法：`GST_DEBUG=flvmux:5` 看它在等谁
2. **时间戳跳变**：源的时间戳回退或大幅跳变时，mux 会告警甚至丢数据。采集设备热插拔、笔记本休眠唤醒后常见

时钟方面，让**音频源提供 pipeline clock**（`pulsesrc provide-clock=true` 是默认行为），音频时钟比系统单调钟更贴近播放节拍，音画不同步的概率更低。

### 4.4 断线重连：最容易被低估的工程难点

生产环境网络不可能稳定，`rtmp2sink` 没有内建重连。断流后 pipeline 会向总线报 error，此时整个管线状态已不可信，**正确姿势是整个重建**：

```{code-block} c
:caption: 重连的核心逻辑（伪代码）
:linenos:

void on_bus_error(GstBus *bus, GstMessage *msg, App *app) {
    // 1. 停掉并销毁整条管线（编码器内部状态已不可复用）
    gst_element_set_state(app->pipeline, GST_STATE_NULL);
    gst_object_unref(app->pipeline);

    // 2. 重建管线（延迟一小段做退避，避免服务器拒绝时打转）
    g_usleep(app->backoff_ms * 1000);
    app->backoff_ms = MIN(app->backoff_ms * 2, 30000);

    // 3. 重建后立刻请求一个关键帧，让观众端尽快恢复
    GstEvent *fku = gst_video_event_new_upstream_force_key_unit(
        GST_CLOCK_TIME_NONE, TRUE, 0);
    gst_element_send_event(app->pipeline, fku);

    gst_element_set_state(app->pipeline, GST_STATE_PLAYING);
}
```

要点有三：

- **重连后立刻 force-keyframe**。否则观众要等最多一个 GOP（2 秒）黑屏
- **退避（backoff）必须有**，指数增长封顶 30 秒，否则服务器故障时会形成重连风暴
- 时间戳基准随新 pipeline 重置，不用担心新旧时间戳串台

### 4.5 码率自适应：没有反馈，就自己造信号

RTMP 是纯 TCP 单向推流，**协议层没有任何拥塞反馈**（这是和 WebRTC GCC 那套闭环最大的差别，见 [QoS 篇](../3.qos/gcc.md)）。想自适应，只能从管线内部找信号：

- **队列水位**：监听 queue 的 `current-level-time`，持续高于阈值 = 发送能力跟不上产出
- **编码耗时**：编码一帧的 wall time 逼近帧间隔 = CPU 到极限了

拿到信号后直接改编码器属性——`x264enc` 的 `bitrate` 是运行时可改的（mutable in PLAYING）：

```{code-block} c
:caption: 拥塞时动态降码率
:linenos:

// 检测到队列水位持续 > 2 秒，主动降码率 30%
g_object_set(app->encoder, "bitrate", app->current_bitrate * 7 / 10, NULL);
// 关键：降码率后立刻申请关键帧，让新的码率状态尽快生效
```

```{note}
x264enc 的 `bitrate` 属性标记为 MUTABLE_PLAYING，可以安全地在推流中修改。多数硬编插件也支持，但行为差异较大，改完最好请求一次 force-keyframe 让服务器端尽快感知。
```

### 4.6 内存与拷贝路径

推流管线的隐性开销大头是**内存拷贝**。典型的浪费路径：摄像头出帧 → `videoconvert` 拷一次 → 缩放再拷一次 → 编码器输入又拷一次。优化思路：

- **源端 caps 直接对齐编码器输入**：分辨率、像素格式在 `v4l2src` 的 caps filter 上一步到位，`videoconvert` 空转（caps 相同时不下行拷贝）
- 硬编路径用 `glupload`/`gldownload` 走 GPU 内存，绕开 CPU 拷贝——但只值得在「多路推流」场景做，单路 1080p 的拷贝开销远没有到瓶颈
- 长跑监控 RSS：GStreamer 上游插件偶有 buffer 泄漏，`gst-tracer` 的 memory tracer 可以定位

### 4.7 可观测性：调优之前先能看见

没有数据支撑的调优都是玄学。三个层次的观测手段：

| 层次 | 手段 | 看什么 |
| :--- | :--- | :--- |
| 运行日志 | `GST_DEBUG=2,flvmux:4,rtmp2*:4` | 协商失败、时间戳跳变、断流原因 |
| 管线状态 | 定时读 queue 的 `current-level-*` | 队列水位 = 拥塞/延迟领先指标 |
| 逐帧延迟 | `GST_TRACERS=latency` | 每帧从源到 sink 的实际耗时分布 |

`latency` tracer 是被低估的利器：它能告诉你延迟到底涨在编码、mux 还是发送环节，而不是凭感觉猜。

## 五、延迟构成：优化到极限是什么水平

按 720p@30、本地网络良好的条件，各环节的延迟预算大致是：

| 环节 | 典型耗时 | 说明 |
| :--- | :--- | :--- |
| 采集 | ~33 ms | 一帧的间隔，动不了 |
| 编码（zerolatency） | ~35 ms | 一帧一出的流水线模式 |
| 封装 | < 1 ms | flvmux 几乎零开销 |
| 网络（TCP） | 10 ~ 数千 ms | **唯一的大头，且不可控** |

也就是说发送端能控制的部分可以压到 **70ms 以内**，观众端感受到的 1~5 秒延迟，几乎全部来自 TCP 缓冲、服务器分发和播放器缓冲。这解释了一个常见误区：**在推流端无限制地调小队列，对端到端延迟收益甚微，还搭上画质**——把发送端做到「不积压、不累积」就到头了。

## 六、上线路前检查清单

- [ ] `h264parse config-interval=-1` 配了（否则晚加入观众黑屏）
- [ ] GOP = 2 秒（`key-int-max` = 2 × 帧率）
- [ ] `tune=zerolatency`，没有 B 帧
- [ ] 所有 queue 有界 + `leaky=downstream`（延迟不累积）
- [ ] 断线重连带指数退避，重连后 force-keyframe
- [ ] 音频分支独立于视频分支的错误处理（音频挂了视频不能陪葬）
- [ ] 硬编做过 24h 长跑：内存平稳、DTS 单调
- [ ] 有队列水位监控，并接了动态码率逻辑

## 小结

GStreamer 推 RTMP 的流程本身不复杂——管线五件套（源、编码、parse、mux、sink）拼起来就能跑。真正的难点全在「跑起来之后」：

1. **编码器选型**是性能的天花板，硬编省 CPU 但要为它补驱动层面的课
2. **队列策略**决定了延迟是「恒定的小」还是「持续增长的大」，直播场景永远丢老帧
3. **断线重连**和**码率自适应**是协议不给你、只能自己在管线里造的能力
4. 端到端延迟的大头在网络，发送端优化到「不积压」即止，别过度

```{todo}
实测数据篇：用 GST_TRACERS=latency 对比 x264enc 与 nvh264enc 在同机上的逐帧延迟分布
```

```{todo}
GStreamer 内核机制篇：从 GstBuffer / GstBufferPool 到零拷贝的完整路径
```
