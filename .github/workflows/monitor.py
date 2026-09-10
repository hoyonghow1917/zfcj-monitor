import os
import json
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.header import Header

# ========== 配置区 ==========
URL = "https://zfcj.gz.gov.cn/gkmlpt/index"
SEEN_FILE = "seen.json"
# ============================

def load_seen():
    """读取已通知过的链接集合"""
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    """把已通知链接写回文件"""
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)

def fetch_articles():
    """抓取页面，返回文章列表 [{title, url}, ...]"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding  # 自动处理中文编码
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = []
    # 遍历页面所有链接，筛选出文章链接
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)

        # 过滤条件：有标题、链接包含文章特征
        if not title or len(title) < 5:
            continue
        if "content" not in href and "post" not in href and "gkmlpt" not in href:
            continue

        # 补全相对链接
        if href.startswith("/"):
            href = "https://zfcj.gz.gov.cn" + href
        elif not href.startswith("http"):
            href = "https://zfcj.gz.gov.cn/" + href

        articles.append({"title": title, "url": href})

    # 去重（同一链接只保留一次）
    seen_urls = set()
    unique = []
    for art in articles:
        if art["url"] not in seen_urls:
            seen_urls.add(art["url"])
            unique.append(art)

    return unique

def send_mail(new_articles):
    """发送邮件通知"""
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    to = os.environ["MAIL_TO"]

    # 邮件正文
    lines = [f"住建局信息公开有新内容，共 {len(new_articles)} 条：\n"]
    for i, art in enumerate(new_articles, 1):
        lines.append(f"{i}. {art['title']}")
        lines.append(f"   {art['url']}\n")
    content = "\n".join(lines)

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = Header(f"住建局信息公开更新 ({len(new_articles)}条)", "utf-8")
    msg["From"] = user
    msg["To"] = to

    # 根据端口选择 SSL 或 STARTTLS
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.starttls()

    server.login(user, password)
    server.sendmail(user, [to], msg.as_string())
    server.quit()

def main():
    print("开始抓取页面...")
    seen = load_seen()
    print(f"已记录 {len(seen)} 条历史链接")

    articles = fetch_articles()
    print(f"本次抓取到 {len(articles)} 条链接")

    # 筛选出新链接
    new_articles = [a for a in articles if a["url"] not in seen]
    print(f"其中新链接 {len(new_articles)} 条")

    if new_articles:
        send_mail(new_articles)
        print("邮件已发送")
        seen.update(a["url"] for a in new_articles)
        save_seen(seen)
        print("seen.json 已更新")
    else:
        print("无新内容，不发送邮件")

if __name__ == "__main__":
    main()
