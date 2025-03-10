import re

from bs4 import BeautifulSoup

class Parser:
    @staticmethod
    def parse_date(date_string):
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
    @staticmethod
    def extract_dates(resopnse):
        return [title['main'] for title in resopnse['titles'] if title['main'] != "會計項目"]

    @staticmethod
    def extract_total_shares_and_year(html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        target_td = soup.find("td", string="實際發行總股數")
        next_td = target_td.find_next_sibling("td").find_next_sibling("td")
        return int(next_td.text.strip().replace(",", "")), soup.find("input", {"name": "Q2V"})["value"]