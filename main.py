import streamlit as st
import json
import pandas as pd

from openai_client import OpenAIClient
from fiancial_statement.analyzer import Analyzer
from fiancial_statement.calculator import Calculator

# Streamlit 應用程式標題
st.set_page_config(page_title="AI 財務顧問", page_icon="📊")
st.title("🕵️‍♂️ 你的 AI 財務顧問")
st.markdown("提供 Altman Z-Score、F-Score、M-Score 以及 AI 財務分析報告。")

# 輸入股票代號
stock_code = st.text_input("📌 請輸入您要查詢的股票代號:")
if st.button("開始分析") and stock_code:

    with st.spinner(f"📊 正在分析股票代號: {stock_code}...", show_time=True):

        ttm = {'stock_code': stock_code}
        analyzer = Analyzer(stock_code)

        analyzer.retrieve_trailing_twelve_months("BS")
        analyzer.retrieve_trailing_twelve_months("CI")
        analyzer.retrieve_trailing_twelve_months("CF")
        year = analyzer.year
        season = analyzer.season
        ttm[year] = analyzer.calculate_ttm(year, season)

        analyzer.retrieve_trailing_twelve_months("BS", year - 1, season)
        analyzer.retrieve_trailing_twelve_months("CI", year - 1, season)
        analyzer.retrieve_trailing_twelve_months("CF", year - 1, season)
        ttm[year - 1] = analyzer.calculate_ttm(year - 1, season)

        analyzer.retrieve_trailing_twelve_months("BS", year - 2, season)
        analyzer.retrieve_trailing_twelve_months("CI", year - 2, season)
        analyzer.retrieve_trailing_twelve_months("CF", year - 2, season)
        ttm[year - 2] = analyzer.calculate_ttm(year - 2, season)
    
    # 計算財務指標
    calculator = Calculator(ttm, year, season)
    z_score_data = calculator.calculate_z_score()
    f_score_data = calculator.calculate_f_score()
    m_score_data = calculator.calculate_m_score()

        # 顯示財務指標圖表
    def render_custom_progress(value, thresholds, colors, labels):
        min_val, max_val = thresholds[0], thresholds[-1]
        percent = (value - min_val) / (max_val - min_val) * 100
        percent = max(0, min(percent, 100))  # 確保範圍在 0% - 100%
        gradient = f"linear-gradient(to right, {colors[0]} 0%, {colors[1]} 50%, {colors[2]} 100%)"
        progress_html = f"""
        <div style="margin-bottom: 40px">
            <div style="position: relative; width: 100%; height: 30px; background: {gradient}; border-radius: 8px; line-height: 30px; text-align: center; color: white; font-weight: bold;">
                <span style="position: absolute; left: 10%; transform: translateX(-50%);">{labels[0]}</span>
                <span style="position: absolute; left: 90%; transform: translateX(-50%);">{labels[1]}</span>
            </div>
            <div style="position: relative; width: 100%; height: 0;">
                <div style="position: absolute; left: {percent}%; top: 0px; transform: translateX(-50%); font-size: 18px; font-weight: bold;">
                    ▲
                </div>
                <div style="position: absolute; left: {percent}%; top: 20px; transform: translateX(-50%); font-size: 16px; font-weight: bold;">
                    {value}
                </div>
            </div>
        </div>
        """
        st.markdown(progress_html, unsafe_allow_html=True)
    
    st.markdown(f"**Altman Z-Score**")
    render_custom_progress(z_score_data['Z-score'], [1.8, 2.9], ["red", "yellow", "green"], ["Distress", "Safe"])

    f_value = 7
    st.markdown(f"**Piotroski F-Score**")
    render_custom_progress(f_score_data['F-score'], [0, 9], ["red", "yellow", "green"], ["Weak", "Strong"])

    m_value = -2.49
    st.markdown(f"**Beneish M-Score**")
    render_custom_progress(m_score_data['M-score'], [-2, -1.78], ["green", "yellow", "red"], ["Deceptive", "Truthful"])
    
    st.markdown(f"""<div style="margin-bottom: 40px"></div>""", unsafe_allow_html=True)
    
    # 顯示財務數據
    st.subheader("📈 財務健康指標")
    st.write("**Altman Z-Score**")
    st.dataframe(pd.DataFrame(z_score_data.items(), columns=["指標", "數值"]), hide_index=True)
    st.write("**F-Score**")
    st.dataframe(pd.DataFrame(f_score_data.items(), columns=["指標", "數值"]), hide_index=True)
    st.write("**M-Score**")
    st.dataframe(pd.DataFrame(m_score_data.items(), columns=["指標", "數值"]), hide_index=True)
    
    # AI 分析報告
    st.subheader("🤖 AI 分析報告")
    with st.spinner("🤖 AI 正在分析財務狀況..."):
        data = {'z_score': z_score_data, 'f_score': f_score_data, 'm_score': m_score_data}
        openai_client = OpenAIClient()
        response = openai_client.get_response(json.dumps(data, ensure_ascii=False, indent=2), "分析這家公司")
    st.write(response)