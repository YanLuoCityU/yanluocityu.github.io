# 网站模块与核心文件说明

## 当前网站模块

### 首页 About Me
- 源文件：`_pages/about.md`
- 配置文件：`_config.yml`
- 头像文件：`images/profile-20260318.png`
- 作用：展示个人简介、研究兴趣、教育背景、Research Highlights，以及侧边栏个人信息。

### Publications
- 页面文件：`_pages/publications.html`
- 数据来源：`_publications/`
- 渲染模板：`_includes/archive-single.html`
- 补充数据：`_data/journal_metrics.yml`、`files/orcid-bib/`
- 作用：展示论文、作者、期刊、年份、IF 和 JCR。

### Research Highlights
- 页面位置：`_pages/about.md` 首页内部
- 数据来源：`_publications/`
- 作用：展示重点论文卡片，并链接到媒体报道页。

### News / Media Coverage
- 页面文件：`_pages/research-highlights-media.html`
- 自动数据：`_data/research_highlights_media.json`
- 手工修正：`_data/research_highlights_media_manual.yml`
- 同步脚本：`scripts/sync_research_highlights_media.py`
- 当前逻辑：先使用自动抓取的 JSON 作为基础数据，再用手工 YAML 覆盖摘要和需要人工修正的报道列表。
- 作用：展示重点论文的英文和中文媒体报道。

### Presentations
- 页面文件：`_pages/talks.html`
- 作用：展示 oral presentations 和 posters。
- 当前为手写页面，不再依赖 `_talks/`。

### Teaching
- 页面文件：`_pages/teaching.md`
- 作用：展示课程名称、role、年份和学校。
- 当前为手写 Markdown 页面，不再依赖 `_teaching/`。

### Honors
- 页面文件：`_pages/honors.md`
- 作用：展示 awards 和 scholarships。

### Service
- 页面文件：`_pages/service.md`
- 作用：展示 journal reviewer 等 professional service。

### 顶部导航
- 配置文件：`_data/navigation.yml`
- 作用：控制顶部导航显示哪些栏目。

## 当前保留的核心文件
- `_config.yml`
- `_config_dev.yml`
- `_data/navigation.yml`
- `_pages/about.md`
- `_pages/publications.html`
- `_pages/research-highlights-media.html`
- `_pages/talks.html`
- `_pages/teaching.md`
- `_pages/honors.md`
- `_pages/service.md`
- `_publications/`
- `_data/journal_metrics.yml`
- `_data/research_highlights_media.json`
- `_data/research_highlights_media_manual.yml`
- `_includes/archive-single.html`
- `_layouts/`
- `_includes/`
- `_sass/`
- `assets/`
- `images/profile-20260318.png`
- `files/orcid-bib/`
- `scripts/sync_orcid_publications.py`
- `scripts/sync_journal_metrics.py`
- `scripts/sync_research_highlights_media.py`
- `.github/workflows/sync_orcid_publications.yml`
- `.github/workflows/sync_journal_metrics.yml`
- `Gemfile`
- `Gemfile.lock`

## 已移除的旧链路
- `_talks/`
- `_teaching/`
- `_portfolio/`
- `_posts/`
- `_pages/cv.md`
- `_pages/cv-json.md`
- `_data/cv.json`
- `scripts/cv_markdown_to_json.py`
- `scripts/update_cv_json.sh`
- `markdown_generator/`
- `.github/workflows/scrape_talks.yml`

## 当前自动化脚本
- `scripts/sync_orcid_publications.py`：从 ORCID 自动同步 publications 到 `_publications/`，并生成 `files/orcid-bib/`。
- `scripts/sync_journal_metrics.py`：更新 `_data/journal_metrics.yml` 中的期刊 IF / JCR。
- `scripts/sync_research_highlights_media.py`：抓取 Nature metrics 基础媒体数据，写入 `_data/research_highlights_media.json`。

## ORCID 自动更新规则
如果通过抓取 ORCID 自动更新 publications，并且以后修改更新规则，请继续保留以下原则：
- 只同步论文类条目到 `_publications/`。
- 不要把 `conference-paper`、`conference-abstract`、`conference-poster`、`conference-presentation` 等会议条目更新到 Publications。
- conference 相关内容应维护在 Presentations 模块，而不是 Publications。

## 维护时怎么判断该改哪里
- 改页面结构：改 `_pages/`
- 改论文内容：改 `_publications/` 或 ORCID 同步脚本
- 改期刊指标：改 `_data/journal_metrics.yml` 或期刊指标同步脚本
- 改媒体报道：优先改 `_data/research_highlights_media_manual.yml`；需要刷新自动底稿时运行 `scripts/sync_research_highlights_media.py`
- 改头像和附件：改 `images/` 或 `files/`
- 改站点身份和导航：改 `_config.yml` 和 `_data/navigation.yml`
