import streamlit as st
import pandas as pd
import re
from bs4 import BeautifulSoup
import io

st.title("✅ 해시태그 분류 실패 진단기")
st.image("fr19.png", use_container_width=True)

st.write("#### 정책지원금 공고 HTML 파일 업로드")
title_file = st.file_uploader("정책지원금 공고 HTML 파일", type=["html", "htm"])

st.write("#### 현재 사용 중인 해시태그 사전 (엑셀) 업로드")
keyword_file = st.file_uploader("해시태그 기준표 파일", type=["xlsx"])

st.caption("💡 해시태그 사전 파일이 없으신가요?")
if st.button("📥 2025 해시태그 분류기준 적용"):
    keyword_file = open("tag_default.xlsx", "rb")
    st.success("✅ 2025 해시태그 기준파일 업로드 완료!")

if title_file and keyword_file:
    # HTML 파싱
    soup = BeautifulSoup(title_file.read(), 'html.parser')
    items = soup.select('li.guide_list_item')
    title_data = []

    for item in items:
        title_tag = item.select_one('h3.guide_list_title')
        hashtag_tags = item.select('ul.hashtag_area > li.hashtag_list')
        title = title_tag.text.strip() if title_tag else None
        hashtags = [tag.text.strip() for tag in hashtag_tags] if hashtag_tags else []

        if title and not hashtags:
            title_data.append({'제목': title})

    df_titles = pd.DataFrame(title_data)
    df_dict = pd.read_excel(keyword_file)

    # 키워드 사전 딕셔너리화
    tag_dict = {}
    exception_dict = {}

    for _, row in df_dict.iterrows():
        tag = row['해시태그']
        includes = str(row['하위키워드']).split(',') if pd.notna(row['하위키워드']) else []
        excludes = str(row['예외키워드']).split(',') if pd.notna(row['예외키워드']) else []
        tag_dict[tag] = [kw.strip() for kw in includes]
        exception_dict[tag] = [kw.strip() for kw in excludes]

    def diagnose(title):
        matched_tags = []
        matched_keywords = []
        blocked_by_exclude = []

        for tag, keywords in tag_dict.items():
            for kw in keywords:
                if kw in title:
                    if any(ex_kw in title for ex_kw in exception_dict.get(tag, [])):
                        blocked_by_exclude.append(tag)
                    else:
                        matched_tags.append(tag)
                        matched_keywords.append(kw)
                        break
        return matched_tags, matched_keywords, blocked_by_exclude

    results = []
    for title in df_titles['제목']:
        tags, kws, blocked = diagnose(title)
        results.append({
            '제목': title,
            '매칭된 해시태그': ', '.join(tags),
            '매칭된 하위키워드': ', '.join(kws),
            '예외 키워드로 막힌 태그': ', '.join(blocked)
        })

    df_result = pd.DataFrame(results)
    st.success(f"총 {len(df_result)}건 진단 완료")
    st.dataframe(df_result)

    st.download_button(
        label="📥 결과 CSV 다운로드",
        data=df_result.to_csv(index=False, encoding='utf-8-sig'),
        file_name='해시태그_진단결과.csv',
        mime='text/csv'
    )

    # ---------------- 시각화 ----------------
    st.subheader("📊 해시태그 매칭 분포 요약")

    def display_ranked_counts(column_name, title):
        flat_values = df_result[column_name].dropna().str.split(', ').explode()
        flat_values = flat_values[flat_values != '']  # 빈 문자열 제거
        value_counts = flat_values.value_counts()
        total = value_counts.sum()

        if not value_counts.empty:
            st.markdown(f"**{title} (Top 10)**")
            for i, (label, count) in enumerate(value_counts.head(10).items(), 1):
                percent = (count / total) * 100
                st.markdown(f"{i}. `{label}` — {percent:.1f}%")
        else:
            st.info(f"'{column_name}'에 대한 데이터가 없습니다.")

    display_ranked_counts('매칭된 해시태그', "✔️ 매칭된 해시태그 분포")
    display_ranked_counts('매칭된 하위키워드', "🔍 매칭된 하위키워드 분포")
    display_ranked_counts('예외 키워드로 막힌 태그', "🚫 예외 키워드로 차단된 태그 분포")
