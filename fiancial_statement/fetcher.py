import json
import requests
import streamlit as st

from fiancial_statement.parser import Parser

class Fetcher:

    BASE_URLS = {
        "BS": "https://mops.twse.com.tw/mops/api/t164sb03",
        "CI": "https://mops.twse.com.tw/mops/api/t164sb04",
        "CF": "https://mops.twse.com.tw/mops/api/t164sb05"
     }

    def __init__(self, stock_code):
        self.stock_code = stock_code

    def request_financial_statement(self, url, dataType, year, season):
        payload = {
            "companyId": self.stock_code,
            "dataType": dataType,
            "season": season,
            "year": year,
            "subsidiaryCompanyId": ""
        }
        headers = {
            "Content-Type":"application/json",
            "User-Agent":'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0'
        }
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        return response.json()['result']

    def fetch_data(self, type, year, season):
        # st.write(f"[取得數據] 正在抓取股票 {self.stock_code} 的資料，報表類型: {type}，年份: {year}，季度: {season}")
        url = self.BASE_URLS[type]
        dataType = 1 if year == "LASTEST" and season == "LASTEST" else 2
        resopnse = self.request_financial_statement(url, dataType, year, season)
        return int(resopnse['year']), int(resopnse['season']), Parser.extract_dates(resopnse), resopnse['reportList']

    def request_distribution_profile_of_share_ownership(self, url, year = "LASTEST"):
        data = {
            "encodeURIComponent": 1, "step": 1, "firstin": 1, "off": 1, "keyword4" : "", "code1" : "","TYPEK2": "", "checkbtn": "",
            "queryName": "co_id", "t05st29_c_ifrs": "N", "t05st30_c_ifrs": "N", "inpuType": "co_id", "TYPEK": "all",
            "isnew": "true" if year == "LASTEST" else "false",
            "co_id": self.stock_code,
            "year": year,
        }
        response = requests.post('https://mopsov.twse.com.tw/mops/web/ajax_t16sn02', data=data)
        return response.text