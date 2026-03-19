---
permalink: /
title: "About Me"
author_profile: true
redirect_from:
  - /about/
  - /about.html
---

I am a PhD candidate in the Department of Data Science, College of Computing, City University of Hong Kong, where I work under the supervision of [Prof Qingpeng Zhang](https://datascience.hku.hk/people/qingpeng-zhang/). Prior to joining CityU, I received an MSc in Epidemiology and Biostatistics from Peking University in 2022 under the supervision of [Prof Beibei Xu](https://medic.bjmu.edu.cn/jyjx/szll/index.htm), and a Bachelor's degree in Medicine from Peking University in 2020.

My research lies at the intersection of data science and epidemiology, with a focus on leveraging large-scale biobanks, cross-national aging cohorts, and real-world electronic health records to address population health challenges. I am particularly interested in developing AI-driven multiomics models for personalized disease risk prediction, uncovering the multi-dimensional determinants of healthy longevity, and characterizing the dynamic trajectories of aging. I welcome opportunities for research collaboration and discussion.

Research Interests
======
- Machine learning
- Deep learning
- Social determinants of health
- Multiomics analysis
- Aging and frailty research

Education
======
- **PhD in Data Science**, City University of Hong Kong (Current)
- **MSc in Epidemiology and Health Statistics**, Peking University, 2022
- **BM in Preventive Medicine**, Peking University, 2020

Research Highlights
======
{% include base_path %}
{% assign sorted_publications = site.publications | sort: 'date' | reverse %}
{% assign highlight_multiomics = nil %}
{% assign highlight_internet = nil %}
{% for post in sorted_publications %}
  {% if post.title == 'AI-based multiomics profiling reveals complementary omics contributions to personalized prediction of cardiovascular disease' %}
    {% assign highlight_multiomics = post %}
  {% endif %}
  {% if post.title contains 'Positive association between Internet use and mental health among adults aged' %}
    {% assign highlight_internet = post %}
  {% endif %}
{% endfor %}

<style>
.research-highlights-grid {
  display: grid;
  gap: 1.5rem;
  margin-top: 1rem;
}

@media (min-width: 960px) {
  .research-highlights-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.research-highlight-card {
  padding: 1.4rem 1.5rem;
  border: 1px solid #d8e0ea;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fafc 100%);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.research-highlight-top {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 0.75rem;
}

.research-highlight-badge {
  display: inline-block;
  padding: 0.28rem 0.72rem;
  border-radius: 999px;
  background: #e6fffb;
  color: #115e59;
  font-size: 0.78rem;
  font-weight: 700;
  white-space: nowrap;
}

.research-highlight-card h2 {
  margin: 0 0 0.7rem 0;
  font-size: 1.12rem;
  line-height: 1.45;
}

.research-highlight-meta {
  margin: 0 0 1rem 0;
  color: #475569;
  font-size: 0.95rem;
}

.research-highlight-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin: 0;
}

.research-highlight-link,
.research-highlight-tag {
  display: inline-flex;
  align-items: center;
  padding: 0.45rem 0.8rem;
  border-radius: 999px;
  font-size: 0.92rem;
  font-weight: 700;
  text-decoration: none;
}

.research-highlight-link {
  background: #0f766e;
  color: #ffffff;
}

.research-highlight-link:hover {
  color: #ffffff;
}

.research-highlight-tag {
  background: #f1f5f9;
  color: #475569;
}
</style>

<div class="research-highlights-grid">
  {% if highlight_multiomics %}
  <section class="research-highlight-card">
    <div class="research-highlight-top">
      <span class="research-highlight-badge">{{ highlight_multiomics.venue }}</span>
    </div>
    <h2><a href="{{ highlight_multiomics.paperurl }}">{{ highlight_multiomics.title }}</a></h2>
    <p class="research-highlight-meta">{{ highlight_multiomics.date | date: "%Y" }}</p>
    <p class="research-highlight-links">
      <a class="research-highlight-link" href="{{ highlight_multiomics.paperurl }}">Paper</a>
      <a class="research-highlight-tag" href="{{ base_path }}/research-highlights/media/#multiomics-cvd">News / Media Coverage</a>
    </p>
  </section>
  {% endif %}

  {% if highlight_internet %}
  <section class="research-highlight-card">
    <div class="research-highlight-top">
      <span class="research-highlight-badge">{{ highlight_internet.venue }}</span>
    </div>
    <h2><a href="{{ highlight_internet.paperurl }}">{{ highlight_internet.title }}</a></h2>
    <p class="research-highlight-meta">{{ highlight_internet.date | date: "%Y" }}</p>
    <p class="research-highlight-links">
      <a class="research-highlight-link" href="{{ highlight_internet.paperurl }}">Paper</a>
      <a class="research-highlight-tag" href="{{ base_path }}/research-highlights/media/#internet-mental-health">News / Media Coverage</a>
    </p>
  </section>
  {% endif %}
</div>
