import re
import streamlit as st

from fiancial_statement.parser import Parser
from fiancial_statement.fetcher import Fetcher



class Analyzer:

    def __init__(self, stock_code):
      self.fetcher = Fetcher(stock_code)
      self.result = {}

    def retrieve_trailing_twelve_months(self, type, year="LASTEST", season="LASTEST"):

      # 獲取最新的財務數據
      year, season, dates, datas = self.fetcher.fetch_data(type, year, season)
      self.parse_financial_statement(type, dates, datas, season)

      # 如果不是 Q4，則需要補齊去年同季的數據
      if season != 4:
        self.fetch_and_parse(type, year - 1, season)
        # 如果是 CI 或 CF 表 需要補齊去年 Q4 的數據
        if type in ["CI", "CF"]:
          self.fetch_and_parse(type, year - 1, 4)

      self.year = year
      self.season = season

    def fetch_and_parse(self, type, year, season):
      # 根據財報類型、年份、季度抓取數據並解析
      year, season, dates, datas = self.fetcher.fetch_data(type, year, season)
      self.parse_financial_statement(type, dates, datas, season)

    def add_item_to_result(self, year, season, item_name, amount):
      self.result.setdefault(year, {}).setdefault(season,{})[item_name] = amount

    def parse_financial_statement(self, type, dates, datas, season):
      # 根據類型解析財報
      if type == "BS":
        self.parse_balance_sheet(dates, datas, season)
      elif type == "CI":
        self.parse_comprehensive_income(dates, datas, season)
      elif type == "CF":
        self.parse_cash_flow(dates, datas, season)

    def parse_balance_sheet(self, dates, datas, season):
      for data in datas:
        item_name = re.sub(r'\s+', '', data[0])
        for i, date in enumerate(dates):
          year, season = Parser.parse_date(date)
          amount = data[i * 2 + 1].replace(' ', '').replace(',', '')
          if amount != "":
            self.result.setdefault(year, {}).setdefault(season,{})[item_name] = float(amount)

    def parse_comprehensive_income(self, dates, datas, season):
      for data in datas:
        item_name = re.sub(r'\s+', '', data[0])
        for i, date in enumerate(dates):
          year, season = Parser.parse_date(date)
          if season == 4:
            amount = data[i * 2 + 1].replace(' ', '').replace(',', '')
          else:
            amount = data[i * 2 + 1].replace(' ', '').replace(',', '')
          if amount != "":
            self.result.setdefault(year, {}).setdefault(season,{})[item_name] = float(amount)

    def parse_cash_flow(self, dates, datas, season):
      for data in datas:
          item_name = re.sub(r'\s+', '', data[0])
          for i, date in enumerate(dates):
            year, season = Parser.parse_date(date)
            amount = data[i + 1].replace(' ', '').replace(',', '')
            if amount != "":
              self.result.setdefault(year, {}).setdefault(season,{})[item_name] = float(amount)

    def calculate_ttm(self, year, season):
      # st.write("[整理數據] 正在計算過去12個月資料(TTM)\n")
      data = {}
      for key in list(self.result[year][season]):
        if season == 4:
          data[key] = self.result[year][season][key]
        else:
          current_value = self.result[year][season].get(key, 0)
          previous_next_season = self.result.get(year - 1,{}).get(season + 1,{}).get(key, 0)
          previous_value = self.result.get(year - 1,{}).get(season,{}).get(key, 0)
          data[key] = current_value + previous_next_season - previous_value
      return data