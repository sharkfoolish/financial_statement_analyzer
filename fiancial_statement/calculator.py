import yfinance

from fiancial_statement.parser import Parser
from fiancial_statement.fetcher import Fetcher


class Calculator:

    def __init__(self, data, year, season):
        self.data = data # TTM
        self.year = year
        self.season = season

    def get_market_cap(self, stock_code):
        stock = yfinance.Ticker(f'{stock_code}.TW')
        market_cap = stock.info.get('marketCap', 'N/A')
        return market_cap

    def is_no_new_shares(self, stock_code):
        financial_statement_fetcher = Fetcher(stock_code)
        html_content = financial_statement_fetcher.request_distribution_profile_of_share_ownership(stock_code)
        total_shares, year = Parser.extract_total_shares_and_year(html_content)
        html_content = financial_statement_fetcher.request_distribution_profile_of_share_ownership(stock_code, int(year) - 1)
        total_shares_last_year, year = Parser.extract_total_shares_and_year(html_content)
        return total_shares == total_shares_last_year

    def calculate_z_score(self):
        print("[模型分析] 正在計算財務比率（Z-score）")
        market_cap = self.get_market_cap(self.data['stock_code'])
        total_assets = self.data[self.year]["資產總額"]
        A = (self.data[self.year]["流動資產合計"] - self.data[self.year]["流動負債合計"]) / total_assets
        B = self.data[self.year]["保留盈餘合計"] / total_assets
        C = (self.data[self.year]["本期稅前淨利（淨損）"] + self.data[self.year]["利息收入"] + self.data[self.year]["折舊費用"] + self.data[self.year]["攤銷費用"]) / total_assets
        D = (market_cap / 1000) / self.data[self.year]["負債總額"]
        E = self.data[self.year]["營業收入合計"] / total_assets
        z_score = 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1 * E
        return {
            "營運資金 / 資產總額": round(A, 2),
            "保留盈餘 / 資產總額": round(B, 2),
            "稅前息前折舊攤銷前獲利 / 資產總額": round(C, 2),
            "股票市值 / 資產總額": round(D, 2),
            "營業收入 / 資產總額": round(E, 2),
            "Z-score": round(z_score, 2),
            "標準": "小於1.8代表危險、1.8到2.9之間代表適中、大於2.9代表安全"
        }

    def calculate_f_score(self):
        print("[模型分析] 正在計算財務比率（F-score）")
        score = 0

        # 1.獲利性
        current_year_ROA = self.data[self.year]["本期淨利（淨損）"] / ((self.data[self.year]['資產總額']) + (self.data[self.year - 1]['資產總額']) / 2)
        if current_year_ROA > 0 :
          score += 1

        # 當年度ROA>0
        current_year_operating_cash_flow = self.data[self.year]["營業活動之淨現金流入（流出）"]
        if current_year_operating_cash_flow > 0 :
          score += 1

        # 當年度營業現金流>0
        current_year_net_income = self.data[self.year]["本期淨利（淨損）"]
        if current_year_operating_cash_flow > current_year_net_income :
          score += 1
        # 當年度營業現金流>淨利

        # 2.安全性
        current_year_long_term_iabilities = self.data[self.year]["非流動負債合計"]
        last_year_long_term_iabilities = self.data[self.year - 1]["非流動負債合計"]
        if current_year_long_term_iabilities < last_year_long_term_iabilities :
          score += 1
        # 當年度長期負債金額<上一年度

        current_year_current_ratio = self.data[self.year]["流動資產合計"] / self.data[self.year]["流動負債合計"]
        last_year_current_ratio = self.data[self.year - 1]["流動資產合計"] / self.data[self.year - 1]["流動負債合計"]
        if current_year_current_ratio > last_year_current_ratio :
          score += 1
        # 當年度流動比率>上一年度

        # 去年無發行新股
        is_no_new_shares = self.is_no_new_shares(self.data['stock_code'])
        if is_no_new_shares :
          score += 1

        # 成長性
        last_year_ROA = self.data[self.year - 1]["本期淨利（淨損）"] / ((self.data[self.year - 1]['資產總額'] + self.data[self.year - 2]['資產總額']) / 2)
        if current_year_ROA > last_year_ROA :
          score += 1
        # 當年度ROA>上一年度

        current_year_gross_margin = self.data[self.year]["營業收入合計"] - self.data[self.year]["營業成本合計"]/ self.data[self.year]["營業收入合計"]
        last_year_gross_margin = self.data[self.year - 1]["營業收入合計"] - self.data[self.year - 1]["營業成本合計"]/ self.data[self.year - 1]["營業收入合計"]
        if current_year_gross_margin > last_year_gross_margin :
          score += 1
        # 當年度毛利率>上一年度

        current_year_asset_turnover_ratio = self.data[self.year]["營業收入合計"] / ((self.data[self.year]['資產總額'] + self.data[self.year - 1]['資產總額']) / 2)
        last_year_asset_turnover_ratio = self.data[self.year - 1]["營業收入合計"] / ((self.data[self.year - 1]['資產總額'] + self.data[self.year - 2]['資產總額']) / 2)
        if current_year_asset_turnover_ratio > last_year_asset_turnover_ratio :
          score += 1
        # 當年度資產周轉率>上一年度

        return {
            "當年度稅後淨利 / 當年度平均總資產": round(current_year_ROA, 2),
            "當年度營業活動之淨現金流入（流出）": round(current_year_operating_cash_flow, 2),
            "當年度本期淨利（淨損）": round(current_year_net_income, 2),
            "當年度非流動負債合計": round(current_year_long_term_iabilities, 2),
            "上一年度非流動負債合計": round(last_year_long_term_iabilities, 2),
            "當年度流動資產 / 當年度流動負債": round(current_year_current_ratio, 2),
            "上一年度流動資產 / 上一年度流動負債": round(last_year_current_ratio, 2),
            "去年無發行新股" : "是" if is_no_new_shares == True else "否" ,
            "上一年度稅後淨利 / 上一年度平均總資產": round(last_year_ROA, 2),
            "(當年度營業收入 - 當年度營業成本) / 當年度營業收入": round(current_year_gross_margin, 2),
            "(上一年度營業收入 - 上一年度營業成本) / 上一年度營業收入": round(last_year_gross_margin, 2),
            "當年度營業收入 / 當年度平均總資產": round(current_year_asset_turnover_ratio, 2),
            "上一年度營業收入 / 上一年度平均總資產": round(last_year_asset_turnover_ratio, 2),
            "F-score": score,
            "標準": "大於等於8代表非常值得投資"
        }


    def calculate_m_score(self):
        print("[模型分析] 正在計算財務比率（M-score）")
        # Day's Sales in Receivable Index
        dsri = (self.data[self.year]["應收帳款淨額"] / self.data[self.year]["營業收入合計"]) / (self.data[self.year - 1]["應收帳款淨額"] / self.data[self.year - 1]["營業收入合計"])

        # Gross Margin Index
        gmi = (self.data[self.year - 1]["營業毛利（毛損）"] / self.data[self.year - 1]["營業收入合計"]) / (self.data[self.year]["營業毛利（毛損）"] / self.data[self.year]["營業收入合計"])

        # Asset Quality Index
        aqi = (self.data[self.year]["非流動資產合計"] / self.data[self.year]["資產總額"]) / (self.data[self.year - 1]["非流動資產合計"] / self.data[self.year - 1]["資產總額"])

        # Sales Growth Index
        sgi = self.data[self.year]["營業收入合計"] /self.data[self.year - 1]["營業收入合計"]

        #Depreciation Index
        depi = (self.data[self.year - 1]["折舊費用"] / self.data[self.year - 1]["不動產、廠房及設備"]) / (self.data[self.year]["折舊費用"] / self.data[self.year]["不動產、廠房及設備"])

        # Sales, General an Administrative Expense Index
        sgai = (self.data[self.year]["推銷費用"] + self.data[self.year]["管理費用"] / self.data[self.year]["營業收入合計"]) / (self.data[self.year - 1]["推銷費用"] + self.data[self.year - 1]["管理費用"] / self.data[self.year - 1]["營業收入合計"])

        # Leverage Index
        lvgi = (self.data[self.year]["負債總額"] / self.data[self.year]["資產總額"]) / (self.data[self.year - 1]["負債總額"] / self.data[self.year - 1]["資產總額"])

        # Total Accruals to Total Asset
        tata = (self.data[self.year]["本期淨利（淨損）"] - self.data[self.year]["營業活動之淨現金流入（流出）"]) / self.data[self.year]["資產總額"]

        m_score = -4.840 + 0.920 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai - 0.327 * lvgi + 4.697 * tata

        return {
            "當年度應收帳款佔營業收入的比例 / 上一年度應收帳款佔營業收入的比例": round(dsri, 2),
            "上一年度毛利率 / 當年度毛利率": round(gmi, 2),
            "當年度非流動資產佔總資產產占比 / 上一年度非流動資產佔總資產產占比": round(aqi, 2),
            "當年度營業收入 / 上一年度營業收入": round(sgi, 2),
            "上一年度折舊費用 / 當年度折舊費用": round(depi, 2),
            "當年度銷管費用占營業收入的比例 / 上一年度銷管費用占營業收入的比例": round(sgai, 2),
            "當年度總負債佔總資產的比例 / 上一年度總負債佔總資產的比例": round(lvgi, 2),
            "稅後淨利 - 營業活動現金流量 / 總資產" : round(tata, 2),
            "M-score": round(m_score, 2),
            "標準": "小於-2代表造假機率極低、-2到-1.78之間代表可能在進行財務操作、大於-1.78表示造假可能性極高"
        }
