import os
import requests

appid = os.environ["WX_APPID"]
secret = os.environ["WX_APPSECRET"]
userid = os.environ["WX_USERID"]
template_id = os.environ["WX_TEMPLATE_ID"]

def main():
    print("开始强制测试微信推送...")
    
    # 1. 获取 access_token
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"
    token_resp = requests.get(token_url, timeout=30)
    token = token_resp.json().get("access_token")
    
    if not token:
        print("获取 token 失败，返回内容:", token_resp.json())
        return
    print("成功获取 token:", token[:10] + "...")

    # 2. 强制发送一条测试消息
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    payload = {
        "touser": userid,
        "template_id": template_id,
        "data": {
            "title": {"value": "强制测试通知"},
            "content": {"value": "如果你收到了这条消息，说明微信推送完全没问题！问题出在网页抓取。"}
        }
    }
    
    resp = requests.post(url, json=payload, timeout=30)
    print("微信推送结果:", resp.json())

if __name__ == "__main__":
    main()
