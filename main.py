import streamlit as st
import json
import re
import yfinance as yf
import requests
import pandas as pd
import os

from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

class OpenAIClient:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("API_KEY")
        base_url = "https://openrouter.ai/api/v1"
        # Initialize the client with API key and base URL
        self.client = OpenAI(api_key=api_key, base_url=base_url)


    def get_response(self, data, question):

        # Format the question as per the requirement
        question = f'請根據這些數據「{data}」回答「{question}」'

        try:
            # Make the API call to get the response
            response = self.client.chat.completions.create(
                model="meta-llama/llama-3.3-70b-instruct:free",
                messages=[{"role": "user", "content": f"{question}\n"}],
                stream=False
            )
            if response and response.choices:
                # Return the content of the first choice
                return response.choices[0].message.content
            else:
                return "錯誤：未收到有效的回應或選項。"
        except Exception as e:
            # Return error if any occurs
            return f"發生錯誤: {e}"

class FinancialStatementFetcher:

    BASE_URLS = {
        "BS": "https://mops.twse.com.tw/mops/web/ajax_t164sb03",
        "CI": "https://mops.twse.com.tw/mops/web/ajax_t164sb04",
        "CF": "https://mops.twse.com.tw/mops/web/ajax_t164sb05"
    }

    def __init__(self, stock_code):
        self.stock_code = stock_code

    def fetch_data(self, type, year="LASTEST", season="LASTEST"):
        st.write(f"[取得數據] 正在抓取股票 {self.stock_code} 的資料，報表類型: {type}，年份: {year}，季度: {season}")
        form_data = {
            'encodeURIComponent': 1,
            'step': 1,
            'firstin': 1,
            'off': 1,
            'co_id': self.stock_code,
            'isnew': "true" if year == "LASTEST" and season == "LASTEST" else "false",
            'year': year,
            'season': season
        }
        response = requests.post(self.BASE_URLS[type], data=form_data)
        return response.text


class FinancialStatementParser:

    @staticmethod
    def parse_html(html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table', {'class': 'hasBorder'})
        return FinancialStatementParser.extract_table_data(table)

    @staticmethod
    def extract_table_data(table):
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        rows = [
            tr.find_all('td') for tr in table.find_all('tr')[4:]
            if tr.find_all('td')
        ]
        return headers, rows

    @staticmethod
    def parse_year_season(date_string):
        # 匹配 "XXX年第Y季" 格式
        match = re.search(r"(\d+)年(?:第|前)?(\d+)季", date_string)
        if match:
            return int(match.group(1)), int(match.group(2))

        # 匹配 "XXX年度"，預設為 Q4
        match = re.search(r"(\d+)年度", date_string)
        if match:
            return int(match.group(1)), 4

        # 匹配 "XXX年MM月DD日"，對應季度
        season_mapping = {"12月31日": 4, "09月30日": 3, "06月30日": 2, "03月31日": 1}
        for season_date, season in season_mapping.items():
            if season_date in date_string:
                match = re.search(r"(\d+)年", date_string)
                if match:
                    return int(match.group(1)), season


class FinancialStatementAnalyzer:

    def __init__(self, stock_code):
        self.fetcher = FinancialStatementFetcher(stock_code)
        self.data = {'stock_code': stock_code}
        self.result = {}

    def retrieve_trailing_twelve_months(self, type):

        # 獲取最新的財務數據
        latest_html = self.fetcher.fetch_data(type)
        headers, rows = FinancialStatementParser.parse_html(latest_html)

        year, season = FinancialStatementParser.parse_year_season(headers[0])
        self.parse_financial_statement(type, headers, rows, season)

        # 如果不是 Q4，則需要補齊去年同季的數據
        if season != 4:
            self.fetch_and_parse(type, year - 1, season)

        # 如果是 CI 或 CF 表 需要補齊去年 Q4 的數據
        if type in ["CI", "CF"]:
            self.fetch_and_parse(type, year - 1, 4)

        self.calculate_ttm(year, season)

    def fetch_and_parse(self, type, year, season):
        # 根據財報類型、年份、季度抓取數據並解析
        html_content = self.fetcher.fetch_data(type, year, season)
        headers, rows = FinancialStatementParser.parse_html(html_content)
        self.parse_financial_statement(type, headers, rows, season)

    def add_item_to_result(self, year, season, item_name, amount):
        self.result.setdefault(year, {}).setdefault(season,
                                                    {})[item_name] = amount

    def parse_financial_statement(self, type, headers, rows, season):
        # 根據類型解析財報
        if type == "BS":
            self.parse_balance_sheet(headers, rows, season)
        elif type == "CI":
            self.parse_comprehensive_income(headers, rows, season)
        elif type == "CF":
            self.parse_cash_flow(headers, rows, season)

    def parse_balance_sheet(self, headers, rows, season):
        dates = headers[3:5] if season == 4 else headers[3:6]
        for cells in rows:
            item_name = cells[0].get_text(strip=True)
            if not cells[1].get_text(strip=True):
                continue
            for i, date in enumerate(dates):
                year, season = FinancialStatementParser.parse_year_season(date)
                amount = float(cells[i * 2 + 1].get_text(strip=True).replace(
                    ',', ''))
                self.add_item_to_result(year, season, item_name, amount)

    def parse_comprehensive_income(self, headers, rows, season):
        dates = headers[3:5] if season == 4 else headers[5:7]
        for cells in rows:
            item_name = cells[0].get_text(strip=True)
            if not cells[1].get_text(strip=True):
                continue
            for i, date in enumerate(dates):
                year, season = FinancialStatementParser.parse_year_season(date)
                if season == 4:
                    amount = float(
                        cells[i * 2 + 1].get_text(strip=True).replace(',', ''))
                else:
                    amount = float(
                        cells[i * 2 + 5].get_text(strip=True).replace(',', ''))
                self.add_item_to_result(year, season, item_name, amount)

    def parse_cash_flow(self, headers, rows, season):
        dates = headers[3:5]
        for cells in rows:
            item_name = cells[0].get_text(strip=True)
            if not cells[1].get_text(strip=True):
                continue
            for i, date in enumerate(dates):
                year, season = FinancialStatementParser.parse_year_season(date)
                amount = float(cells[i + 1].get_text(strip=True).replace(
                    ',', ''))
                self.add_item_to_result(year, season, item_name, amount)

    def calculate_ttm(self, year, season):
        st.write("[整理數據] 正在計算過去12個月資料(TTM)\n")
        for key in list(self.result[year][season]):
            if season == 4:
                self.data[key] = self.result[year][season][key]
            else:
                current_value = self.result[year][season].get(key, 0)
                previous_next_season = self.result.get(year - 1,
                                                       {}).get(season + 1,
                                                               {}).get(key, 0)
                previous_value = self.result.get(year - 1,
                                                 {}).get(season,
                                                         {}).get(key, 0)
                self.data[
                    key] = current_value + previous_next_season - previous_value


class FinancialModelCalculator:

    def __init__(self, financial_data):
        self.data = financial_data

    def get_market_cap(self, stock_code):
        stock = yf.Ticker(f'{stock_code}.TW')
        market_cap = stock.info.get('marketCap', 'N/A')
        return market_cap
        
    def calculate_z_score(self):
        market_cap = self.get_market_cap(self.data['stock_code'])
        total_assets = self.data["資產總額"]
        A = (self.data["流動資產合計"] - self.data["流動負債合計"]) / total_assets
        B = self.data["保留盈餘合計"] / total_assets
        C = (self.data["本期稅前淨利（淨損）"] + self.data["利息收入"] + self.data["折舊費用"] + self.data["攤銷費用"]) / total_assets
        D = (market_cap / 1000) / self.data["負債總額"]
        E = self.data["營業收入合計"] / total_assets
        z_score = 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1 * E
        return {
            "營運資金 / 資產總額": A, 
            "盈餘公積 + 未分配利潤 / 資產總額": B, 
            "稅、息、折舊攤銷前的獲利 / 資產總額": C, 
            "股票市值 / 資產總額": D, 
            "營業總收入 / 資產總額": E, "Z-score": z_score
        }


# Example usage
st.title("🕵️‍♂️ 你的 AI 財務顧問")
stock_code = st.text_input("請輸入您要查詢的股票代號 :")
if st.button("開始分析") and stock_code:

    with st.spinner(f"股票代號: {stock_code}", show_time=True):
        financial_statement_analyzer = FinancialStatementAnalyzer(stock_code)
        financial_statement_analyzer.retrieve_trailing_twelve_months("BS")
        financial_statement_analyzer.retrieve_trailing_twelve_months("CI")
        financial_statement_analyzer.retrieve_trailing_twelve_months("CF")
    
    st.subheader("📈 Altman Z-Score")
    calculator = FinancialModelCalculator(financial_statement_analyzer.data)
    z_score = calculator.calculate_z_score()
    st.dataframe(pd.DataFrame(z_score.items(), columns=["指標", "數值"]))
    
    with st.spinner("🤖 AI 正在分析財務狀況...", show_time=True):
        openai_client = OpenAIClient()
        response = openai_client.get_response(json.dumps(z_score, ensure_ascii=False, indent=2), "分析這家公司")
    st.subheader("🤖 AI 分析報告")
    st.write(response)