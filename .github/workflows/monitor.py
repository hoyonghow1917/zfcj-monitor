import os
import json
import requests
from bs4 import BeautifulSoup

URL = "https://zfcj.gz.gov.cn/gkmlpt/index"
SEEN_FILE = "seen.json"

# ================= 微信推送模块 =================
def get_access_token(appid, secret):
    """获取微信测试号的 access_token"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"
    resp = requests.get(url, timeout=30)
    return resp.json().get("access_token")

def send_wechat(new_articles):
    appid = os.environ["WX_APPID"]
    secret = os.environ["WX_APPSECRET"]
    userid = os.environ["WX_USERID"]
    template_id = os.environ["WX_TEMPLATE_ID"]
    
    token = get_access_token(appid, secret)
    if not token:
        print("获取 access_token 失败，请检查 appid 和 secret")
        return

    # 限制推送条数，防止消息过长超出微信限制
    max_items = 10
    display_articles = new_articles[:max_items]
    content = "\n".join([f"{a['title']}  {a['url']}" for a in display_articles])
    
    if len(new_articles) > max_items:
        content += f"\n\n... 共 {len(new_articles)} 条，仅显示前 {max_items} 条"

    title = f"住建局更新 ({len(new_articles)}条)"
    
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    payload = {
        "touser": userid,
        "template_id": template_id,
        "data": {
            "title": {"value": title},
            "content": {"value": content}
        }
    }
    resp = requests.post(url, json=payload, timeout=30)
    print("微信推送结果:", resp.json())

# ================= 网页抓取模块 =================
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)

def fetch_articles():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)

        if not title or len(title) < 5:
            continue
        if "content" not in href and "post" not in href and "gkmlpt" not in href:
            continue

        if href.startswith("/"):
            href = "https://zfcj.gz.gov.cn" + href
        elif not href.startswith("http"):
            href = "https://zfcj.gz.gov.cn/" + href

        articles.append({"title": title, "url": href})

    # 去重
    seen_urls = set()
    unique = []
    for art in articles:
        if art["url"] not in seen_urls:
            seen_urls.add(art["url"])
            unique.append(art)
    return unique

# ================= 主流程 =================
def main():
    print("开始抓取页面...")
    seen = load_seen()
    articles = fetch_articles()
    new_articles = [a for a in articles if a["url"] not in seen]

    if new_articles:
        print(f"发现 {len(new_articles)} 条新内容，准备推送...")
        send_wechat(new_articles)
        seen.update(a["url"] for a in new_articles)
        save_seen(seen)
        print("seen.json 已更新")
    else:
        print("无新内容")

if __name__ == "__main__":
    main()
