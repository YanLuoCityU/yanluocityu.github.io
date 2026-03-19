# 网站模块与必要文件说明

## 当前网页模块

### 首页 About Me
- 源文件：_pages/about.md
- 配置文件：_config.yml
- 头像文件：images/profile-20260318.png
- 作用：展示个人简介、研究兴趣、教育背景、Research Highlights，以及侧边栏个人信息。

### Publications
- 页面文件：_pages/publications.html
- 数据来源：_publications/
- 渲染模板：_includes/archive-single.html
- 补充数据：_data/journal_metrics.yml、files/orcid-bib/
- 作用：展示论文、作者、期刊、年份、IF 和 JCR。

### Research Highlights
- 页面位置：_pages/about.md 首页内部
- 数据来源：_publications/
- 作用：展示重点论文卡片，并链接到媒体报道页。

### News / Media Coverage
- 页面文件：_pages/research-highlights-media.html
- 数据文件：_data/research_highlights_media.json、_data/research_highlights_media_manual.yml
- 作用：展示重点论文的英文和中文媒体报道。

### Presentations
- 页面文件：_pages/talks.html
- 作用：展示 oral presentations 和 posters。
- 当前为手写页面，不依赖 _talks/。

### Teaching
- 页面文件：_pages/teaching.md
- 作用：展示课程名称、role、年份和学校。
- 当前为手写 Markdown 页面，不再依赖 _teaching/ 渲染。

### Honors
- 页面文件：_pages/honors.md
- 作用：展示 awards 和 scholarships。

### Service
- 页面文件：_pages/service.md
- 作用：展示 journal reviewer 等 professional service。

### 顶部导航
- 配置文件：_data/navigation.yml
- 作用：控制顶部导航显示哪些栏目。

## 必要的核心文件
- _config.yml
- _config_dev.yml
- _data/navigation.yml
- _pages/about.md
- _pages/publications.html
- _pages/research-highlights-media.html
- _pages/talks.html
- _pages/teaching.md
- _pages/honors.md
- _pages/service.md
- _publications/
- _data/journal_metrics.yml
- _data/research_highlights_media.json
- _data/research_highlights_media_manual.yml
- _includes/archive-single.html
- _layouts/
- _includes/
- _sass/
- assets/
- images/profile-20260318.png
- files/orcid-bib/
- Gemfile
- Gemfile.lock

## 可选自动化脚本
- scripts/sync_orcid_publications.py：从 ORCID 自动同步 publications。
- scripts/sync_journal_metrics.py：更新期刊 IF / JCR。
- scripts/sync_research_highlights_media.py：抓取 Nature metrics 媒体数据。
- scripts/cv_markdown_to_json.py：生成 cv.json。

## ORCID 自动更新规则
如果通过抓取 ORCID 自动更新 publications，并且以后修改更新规则，请继续保留以下原则：
- 只同步论文类条目到 _publications/。
- 不要把 conference-paper、conference-abstract、conference-poster、conference-presentation 等会议条目更新到 Publications。
- conference 相关内容应维护在 Presentations 模块，而不是 Publications。

## 维护时怎么判断该改哪里
- 改页面结构：改 _pages/
- 改论文内容：改 _publications/ 或 ORCID 同步脚本
- 改媒体报道和补充数据：改 _data/
- 改头像和附件：改 images/ 或 files/
- 改站点身份和导航：改 _config.yml 和 _data/navigation.yml
