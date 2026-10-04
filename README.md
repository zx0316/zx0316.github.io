# 流媒体技术笔记

基于 **Sphinx + Furo** 的流媒体 / WebRTC 学习笔记站，
在线地址：<https://zx0316.github.io>

外观：明亮优雅的 Furo 主题，青碧色点缀，自带明暗切换（右上角图标）。

## 本地预览

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

make html                      # 输出到 build/html
open build/html/index.html
```

热重载（改文档自动刷新）：

```bash
pip install sphinx-autobuild
make livehtml                  # http://127.0.0.1:8000
```

## 写新文章

1. 在对应章节目录放一个 `.md`，例如 `source/2.transport/rtp-rtcp.md`；
2. 文件开头用一级标题 `# 标题` 作为页面标题；
3. 在同一级的 `index.md` 的 `toctree` 里加上文件名（不含 `.md`）。

```markdown
```{toctree}
:maxdepth: 2

rtp-rtcp
```
```

文章之间的交叉引用用 `{doc}` 角色：

```markdown
参见 {doc}`../3.qos/gcc`
```

## 常用语法

| 想做的事 | 写法 |
| :--- | :--- |
| 提示框 | ` ```{note} ` / `{tip}` / `{warning}` 指令块 |
| 待办项 | ` ```{todo} ` 指令块 |
| 代码块标题+行号 | ` ```{code-block} cpp ` 配 `:caption:` `:linenos:` |
| 流程图 | ` ```{mermaid} ` 指令块 |

## 目录结构

```
.
├── Makefile                 # make html / make livehtml
├── requirements.txt         # 构建依赖
├── extra/                   # 旧博客 URL 的跳转页（原样拷贝）
└── source/
    ├── conf.py              # 主题（Furo）、扩展、中文字体与配色变量
    ├── index.md             # 首页 + 总目录
    ├── _static/custom.css   # 中文排版微调
    ├── 1.latency/           # 延迟篇
    ├── 2.transport/         # 传输协议篇
    ├── 3.qos/               # QoS 与弱网对抗篇
    └── 4.practice/          # 工程实践篇
```

## 发布

push 到 `main` 后，GitHub Actions（`.github/workflows/pages-deploy.yml`）
自动执行 `sphinx-build` 并部署到 GitHub Pages，无需手动操作。
