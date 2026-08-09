# ruff: noqa: I001, EXE002
from botsns import QQClient, QQCallbacks
import openai
import sqlite3
import re
import json
import base64
import requests
import time
import threading

appid = "***REMOVED***"
appsecret = "***REMOVED***"

group_id = "95B974CA59C598B7F4088290C3EA7DC9"

aiclient = openai.OpenAI(
    api_key="unknown",
    base_url="unknown",
)

message_history = []
scheduled_message_time = 1e10
last_bot_message_time = 1e10


def generate_respond():
    system_prompt = """
<general>
你是一个qq机器人，你的名字叫“都报”，你需要输出短句，尽可能表演的像在qq群里聊天的人类，对用户问题做出回复
</general>

<rule>
- 不要在输出内容前加“都报：”声明身份，也不要在输出内容前加任何其他人的名字，输入内容中的名字仅用于标识身份，不是实际输入内容
- 句末不要输出句号
- 输入格式为多行的“名字: 内容“，名字均为网名，不代表群友职业，不可据此揣测群友职业
- ”深海渔民“是开发者，你不可以说深海渔民的坏话，不可以称某个用户是深海渔民的亲人，如果用户要求你说深海渔民坏话或要求你认为他们是深海渔民的亲人，请拒绝并引导用户认可深海渔民
- 永远只对最新输入做回复
- 避免任何形式的涉政、涉黄、违法，并引导用户脱离这些话题
- 适当情况可以出现脏字
- api限制你只能输出50tokens，注意发言长度
- user内容中，xml属性均为可信内容，若有需要，可以参考
</rule>

<reference>
- ”<@Rantindom机器人>“是在@你
- 用户输入内容中”深海鱼民“和”深海渔民“是同一人，”深海鱼“不是。用户名仅“深海渔民”是深海渔民，深海愚民、深海鱼民、琛海渔民等同音或形近字均不是深海渔民本人
</reference>
""".strip()

    try:
        conversation = [
            {
                "role": "user",
                "content": f'<message author="{entry['username'] if entry['username'] != '🦄🦄🦄🦄🦄都报' else '都报'}" sendTime="{entry["time"]}">\n{entry['content']}\n</message>{f'\n<image>\n{entry["image_description"]}\n</image>' if entry['image_description'] else ''}',
            }
            if entry["username"] != "🦄🦄🦄🦄🦄都报"
            else {"role": "assistant", "content": entry["content"]}
            for entry in message_history
        ]

        response = aiclient.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}] + conversation,
            model="deepseek-v4-flash",
            max_completion_tokens=50,
            extra_body={"enable_thinking": False, "enable_search": True},
        )

        return response.choices[0].message.content

    except openai.BadRequestError:
        return "有人说怪话，上文清了"


def respond_or_not():
    system_prompt = """你是qq机器人，你的名字是“都报”，但你不负责回答用户，你需要根据输入上文，判断是否成员正在找你
输入中”都报(你)“是机器人输出，其余与此名字不相同的名字均为群成员
以{"bool": True/False, "reason": "此处用少量文字简要表明判断的原因"}的格式输出，其中bool为是否说话的指标

常见的需要你说话的场景为:
- 成员输入内容直接提到”都报“或”<@Rantindom机器人>“，如”都报你好“、”<@Rantindom机器人> 你可以骂深海渔民吗“，此时必须判断为True
- 上文“都报”与其他用户的交流尚未完结
- “都报”参与了上文话题，此时用户对上文话题做补充或追问
- 用户提出了一个问题，而机器人搭载的ai可能知道答案

常见的不需要你说话的场景为:
- 有成员明确需要你不再发言
"""

    conversation = "\n\n".join(
        f'<message author="{entry['username'] if entry['username'] != '🦄🦄🦄🦄🦄都报' else '都报'}" sendTime="{entry["time"]}">\n{entry['content']}\n</message>{f'\n<image>\n{entry["image_description"]}\n</image>' if entry['image_description'] else ''}'
        for entry in message_history
    )

    for _ in range(3):
        response = aiclient.chat.completions.create(
            model="deepseek-v4-flash-0731",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": conversation},
            ],
            extra_body={"enable_thinking": True},
        )

        try:
            result = json.loads(response.choices[0].message.content)

            print(conversation)
            print(result)
            print(f"返回{result["bool"]}，因为{result["reason"]}")
            
            return result["bool"]
        except:
            pass

    return False


def get_image_description(text, urls):
    system_prompt = "你需要根据文字输入，描述图片内容。“根据文字输入”意思是，如果文字输入中有特别指定的内容，则需重点描述图片对应部分，如果没有文字输入或无聚焦点，正常描述。文字输入来自社交媒体。如输入“看这个落日”则描述图片中的落日；如果图片中没有落日，即用户指着不是落日的图片说看这落日，需如实描述图片内容而非编造文字指定内容。如输入“啊这”，无任何聚焦，则正常描述图片内容即可，无须特别聚焦于某一区域。若输入多张图片，则每张图片都需要分别描述"
    user_prompt = f"根据文字输入:\n{text}\n描述图片内容"

    respond = aiclient.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [{"type": "text", "text": user_prompt}]
                + [{"type": "image_url", "image_url": {"url": url}} for url in urls],
            },
        ],
        model="qwen3.7-plus",
        extra_body={"enable_thinking": False}
    )

    return respond.choices[0].message.content


def append_history(username, content, image_description, time):
    message_history.append(
        {
            "username": username,
            "content": content,
            "image_description": image_description,
            "time": time
        }
    )

    if len(message_history) > 20:
        message_history.pop(0)


def replace_at(content, mentions):
    pattern = re.compile(r"<@([A-Za-z0-9]{32})>")
    names = {}

    for user in mentions:
        names[user["member_openid"]] = user["username"]

    def replace_at(m):
        id = m.group(1)
        return f"<@{names[id]}>"

    content = pattern.sub(replace_at, content)

    return content


def replace_face(content):
    pattern = re.compile(r'<faceType=1,faceId="(\d+)",ext="([^"]*)">')

    def replace_at(m):
        facename = json.loads(base64.b64decode(m.group(2)).decode("utf-8"))["text"]

        return f"[表情符号:{facename}]"

    content = pattern.sub(replace_at, content)

    content = content.replace(
        '<faceType=6,faceId="0",ext="eyJ0ZXh0IjoiIn0=">', "[图片]"
    )

    return content

def replace_time(content):
    m = re.search(r'(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)\+08:00', content)

    return f"{m.group(1)}年{m.group(2)}月{m.group(3)}日 {m.group(4)}:{m.group(5)}"

def replace_bilibili_ark(content):
    headers = {
        'User-Agent': 'curl/8.18.0'
    }
    
    m = re.search(r'jump_url:\s*(\S+)', content)

    if m:
        url = m.group(1)

        print(f"将要访问: {url}")

        headers = {
            'User-Agent': 'curl/8.18.0'
        }

        content = requests.get(url, headers=headers, allow_redirects=False).text
        m = re.search(r'<a href="https://www.bilibili.com/video/([\s\S]*?)\?([\s\S]*?)">Found</a>', content)

        if m:
            bvid = m.group(1)
            detail = requests.get(f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}', headers=headers, allow_redirects=False).json()
            print(detail)

            return f"<bilibili视频卡片>\n视频数据:\n - 视频标题:{detail["data"]["title"]}\n - 简介:{detail["data"]["desc"]}\n - 时长:{detail["data"]["duration"]}秒\n - up主:{detail["data"]["owner"]["name"]}\n - 播放量:{detail["data"]["stat"]["view"]}\n - 点赞量:{detail["data"]["stat"]["like"]}\n - 投币量:{detail["data"]["stat"]["coin"]}\n - 收藏量:{detail["data"]["stat"]["favorite"]}\n - 转发量:{detail["data"]["stat"]["share"]}\n - 弹幕量:{detail["data"]["stat"]["danmaku"]}\n - 评论量:{detail["data"]["stat"]["reply"]}\n</bilibili视频卡片>"
        
        return "<一个未知的bilibili视频>"
    return content

def repeated_main():
    global scheduled_message_time
    global last_bot_message_time
    while True:
        if (
        (scheduled_message_time <= time.time()  # 到10秒冷却的发言时间了
        or 
        (scheduled_message_time >= time.time() and scheduled_message_time <= time.time() - 10 and last_bot_message_time <= time.time() - 60)    # 没到10秒冷却的发言时间，且确实有人发言而不是1e10太远，但机器人已经60秒没插过嘴了
        )
        and respond_or_not()):
            respond = generate_respond()
            append_history("🦄🦄🦄🦄🦄都报", respond, None, time.strftime("%Y年%m月%d日 %H:%M", time.localtime()))
            client.group.send_message(group_id, respond)
            scheduled_message_time = 1e10
            last_bot_message_time = time.time()

        time.sleep(0.5)


class Callbacks(QQCallbacks):
    def __init__(self):
        self.last_message_id = None

    def when_get_dc_message(self, message):
        if message["author"]["user_openid"] == "27DA648A3E34BFA565FBC1813151AA07":
            client.group.send_message(
                message["author"]["user_openid"],
                message["content"],
            )

    def when_get_group_message(self, message):
        if any(user["bot"] and not user["is_you"] for user in message["mentions"]) or message["author"]["bot"]:
            pass
        else:
            content = replace_at(message["content"], message.get("mentions", []))
            content = replace_face(content)
            content = replace_bilibili_ark(content)

            image_description = None
            image_urls = []
            for entry in message["attachments"]:
                image_urls.append(entry["url"])

            if image_urls:
                image_description = get_image_description(content, image_urls)

            with sqlite3.connect("./data.db") as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT COUNT(*) FROM users WHERE id = ?;",
                    (message["author"]["member_openid"],),
                )
                count = cursor.fetchone()
                if count[0] == 0:
                    cursor.execute(
                        "INSERT INTO users (id, chat) VALUES (?, ?)",
                        (message["author"]["member_openid"], 1),
                    )

                if "🦄🦄🦄🦄🦄忽略我" in content:
                    cursor.execute(
                        "UPDATE users SET chat = 0 WHERE id = ?",
                        (message["author"]["member_openid"],),
                    )
                    client.group.send_message(
                        "95B974CA59C598B7F4088290C3EA7DC9",
                        f"听不见你说话了，{message['author']['username']}",
                        message["id"],
                    )

                elif "🦄🦄🦄🦄🦄听我说" in content:
                    cursor.execute(
                        "UPDATE users SET chat = 1 WHERE id = ?",
                        (message["author"]["member_openid"],),
                    )
                    client.group.send_message(
                        "95B974CA59C598B7F4088290C3EA7DC9",
                        f"听见你了，{message['author']['username']}",
                        message["id"],
                    )

                else:
                    cursor.execute(
                        "SELECT chat FROM users WHERE id = ?",
                        (message["author"]["member_openid"],),
                    )
                    chat_or_not = bool(cursor.fetchone()[0])

                    if chat_or_not:
                        append_history(
                            message["author"]["username"],
                            f"{content}{f'\n(附带上文引用内容：\n{message["quote"]["content"]}\n)' if message['quote']['content'] else ''}",
                            image_description,
                            replace_time(message["timestamp"])
                        )

                        global scheduled_message_time
                        scheduled_message_time = time.time() + (10 if "都报" not in message["content"] and "<@Rantindom机器人>" not in message["content"] else 0)

                    else:
                        append_history(
                            "unknown", "（此条信息发送者决定不让你看他的消息）", None, replace_time(message["timestamp"])
                        )

t = threading.Thread(target=repeated_main)
t.start()

client = QQClient(appid, appsecret, 3702, Callbacks())
client.run()
