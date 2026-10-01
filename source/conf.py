# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- 项目信息 ---------------------------------------------------------------

project = '流媒体技术笔记'
copyright = '2026, zx0316'
author = 'zx0316'
release = '0.1'
language = 'zh_CN'

# -- 通用配置 ---------------------------------------------------------------

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.mathjax',
    'sphinx.ext.graphviz',
    'sphinxcontrib.mermaid',
    'sphinx_copybutton',
]

templates_path = ['_templates']
exclude_patterns = ['_backup', '_build', 'Thumbs.db', '.DS_Store']

# 额外原样拷贝的静态文件：用于保留旧博客 URL 的跳转页
html_extra_path = ['../extra']

# MyST：继续用 Markdown 写作，同时支持 Sphinx 指令
myst_enable_extensions = [
    'colon_fence',
    'deflist',
    'fieldlist',
    'tasklist',
    'attrs_block',
    'linkify',
]
myst_heading_anchors = 3          # 生成可读锚点，便于目录内跳转
myst_footnote_transition = True

# todo 扩展：允许在正文里标 TODO
todo_include_todos = True

# -- HTML 输出 --------------------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_show_sourcelink = False
html_title = '流媒体技术笔记'
html_short_title = '流媒体笔记'

html_theme_options = {
    'navigation_depth': 3,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
    'logo_only': False,
    'prev_next_buttons_location': 'both',
    'style_external_links': True,
}

# -- 代码复制按钮 ------------------------------------------------------------

copybutton_prompt_text = r'>>> |\.\.\. |\$ |> '
copybutton_prompt_is_regexp = True

# -- mermaid ----------------------------------------------------------------

mermaid_version = '11'
mermaid_output_format = 'raw'   # 浏览器端渲染，构建时不需要 mmdc


def setup(app):
    app.add_css_file('custom.css')
