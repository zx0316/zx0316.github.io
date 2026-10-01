# GCC 带宽估计

```{note}
本篇施工中。
```

## 两条控制回路

GCC（Google Congestion Control）不是一个算法，而是两个估计器加一个仲裁：

- **基于延迟的估计**（delay-based）：观察包间延迟的增长趋势，判断链路是否开始排队。
- **基于丢包的估计**（loss-based）：按丢包率直接上调 / 下调发送码率。

最终发送码率取两者的**较小值**。

```{todo}
Trendline 滤波器：为什么用线性回归而不是单点采样
```

```{todo}
Over-use / Under-use / Normal 三种状态机与阈值自适应
```

```{todo}
与 BBR 的思路对比：延迟梯度 vs 带宽时延积
```

## 一个常见的坑

```{warning}
发送码率降下来之后要缓慢回升（加性增），否则会在「码率振荡 → 画面忽好忽坏」之间反复横跳。
```

## 参考

- {doc}`../2.transport/rtp-rtcp` — RTCP 反馈报文是 GCC 的输入源
