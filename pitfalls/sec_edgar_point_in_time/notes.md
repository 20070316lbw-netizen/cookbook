# SEC EDGAR 抓取 + Point-in-Time 对齐(防 look-ahead)

## 一句话

抓 EDGAR 基本面数据时,**对齐基本面到某个时间点 T,必须用 `filed`(财报实际提交日)
当门禁,绝不能用 `end`(财报期末日)**。用 `end` 对齐 = 偷看未来 = 整个回测作废。

---

## EDGAR 接口本身(很简单)

无 API key、无 OAuth,就是 HTTP GET 返回 JSON。

- CIK 映射表(全量,一次性):
  `https://www.sec.gov/files/company_tickers.json`
- CompanyConcept(单公司单指标历史,主力接口):
  `https://data.sec.gov/api/xbrl/companyconcept/CIK{10位补零}/us-gaap/{tag}.json`
  例:`.../CIK0000320193/us-gaap/StockholdersEquity.json`

### 四个坑
1. **强制 User-Agent**,不带直接 403。头里写 `{"User-Agent": "名字 邮箱"}`。
2. **10 请求/秒限制**,抓 500 只要自己 `time.sleep` 控速,否则封 IP。
3. **CIK 必须补零到 10 位**:`320193` → `"0000320193"`。
   做法:`raw["cik_str"].astype(str).str.zfill(10)`(先转 str 才能用 .str.zfill)。
4. **同一个数会重复出现多次**(10-K 里含季度对比表,季报里已报过 → 不同 accn 重复)。
   且修订版(10-K/A)会改数(例:Apple 2007 equity 从 14532 改成 14531)。

### JSON 怎么挖
```python
resp = requests.get(url, headers=HEADERS)   # 注意 .get,不是 requests()
resp.raise_for_status()
raw = resp.json()                            # 拿 dict,不是 .text
records = raw["units"]["USD"]                # 两次取值钻进去 → list of dict
df = pd.DataFrame(records)                   # list of dict 直接成表
```
注意:`units` 下的 key 不一定是 `"USD"`,股数类指标是 `"shares"`。

---

## 核心:Point-in-Time 对齐(这是面试最爱问的点)

### 心智模型
站在时间点 T 往回看,问:**「此刻我手上,这家公司最新的、且已经公开了的 book equity 是多少?」**

### 字段各司其职
| 字段 | 角色 | 用途 |
|------|------|------|
| `filed` | **门禁** | 决定一条记录「何时才允许被看见」。`filed <= T` 才进得来 |
| `end` | **排序键** | 在能看见的记录里,选「财报期最新」的那条 |

### 为什么 end 不能当门禁
真实例子(Apple `StockholdersEquity`):
```
end=2006-09-30, val=9984000000, filed=2009-10-27   ← 财报期 2006,但 2009 才提交!
```
若在 2008 年用 `end` 对齐,会拿到这条 2006 的数 —— 可那时它还没公开,
你根本不可能知道。用 `filed <= T` 就把它挡在门外了。

### 对齐 + 去重逻辑(三步)
```
def get_book_equity_asof(df, asof_date):
    # 1. df[df["filed"] <= asof_date]   ← 门禁:砍掉还没公开的
    # 2. 按 end 分组,组内取 filed 最晚  ← 去重:修订版优先(最新提交最准)
    # 3. 取 end 最大那条的 val           ← 选最新财报期
```

口诀:**filed 当门禁,end 当排序键;同 end 多条,取 filed 最晚。**

---

## 进度锚点(2026-06-09)
- `fetch_cik.py`:CIK 映射表已做好(含补零列 `cik`),`return raw`。
- `fetch_edgar.py`:单只 Apple StockholdersEquity 已能抓 + 挖成 DataFrame(258 行)。
- 下一步:写 `get_book_equity_asof` 把对齐逻辑落地;再扩到 universe 循环 + 控速。
