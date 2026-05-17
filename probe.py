"""快速探测备用数据源是否可用"""
import requests, re, json

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"}

def test(name, url, **kw):
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, **kw)
        print(f"[OK] {name}  status={r.status_code}  len={len(r.text)}")
        print(f"     {r.text[:120]}\n")
        return r.text
    except Exception as e:
        print(f"[FAIL] {name}  {e}\n")
        return None

# 1. 新浪实时行情（已知可用）
test("新浪指数", "https://hq.sinajs.cn/list=s_sh000001")

# 2. 新浪单只基金行情
test("新浪基金报价", "https://hq.sinajs.cn/list=sz161725")

# 3. fundgz 估算净值
test("基金估算净值", "http://fundgz.1234567.com.cn/js/161725.js")

# 4. 天天基金 API（不同于 push2）
test("天天基金净值", "https://fundmobapi.eastmoney.com/FundMApi/FundHisNetList.ashx",
     params={"FCODE":"161725","pageIndex":1,"pageSize":1,"MobileKey":"1","appType":"ttjj"})
