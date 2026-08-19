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
import uuid
import configparser

config = configparser.ConfigParser()
config.read("./config.ini", encoding="utf-8")

appid = config.get("bot", "appid")
appsecret = config.get("bot", "appsecret")
group_id = config.get("bot", "group_id")

aiclient = openai.OpenAI(
    api_key=config.get("ai", "api_key"),
    base_url=config.get("ai", "base_url"),
)
print(f"api: {config.get("ai", "api_key")}")
chat_model = config.get("ai", "chat_model")
multimodal_model = config.get("ai", "multimodal_model")

time_interval_since_last_message = 20   #人类用户发言这么多秒后决策一次机器人是否发言
max_time_interval_since_last_message = 120  # 如果一直有人发言，这么多秒后机器人插不上嘴，则强制决策一次是否插嘴
id_number = 100   # 通过username(id的前id_number位)区分同名用户

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
- 将逗号替换为换行。如果问号和感叹号必须出现，则在其后添加一个换行，如果不出现问号和感叹号不会引起语义歧义，将问号和感叹号替换为换行。换行指“\n”。如将“来了来了，聊点什么？你吃了吗”替换为“来了来了\n聊点什么\n你吃了吗“
- 严禁使用将标点符号换为空格或把空格当标点符号来用的输出方式，例如“来了来了 聊点什么 你吃了吗”
- 输入格式为多行的“名字: 内容“，名字均为网名，不代表群友职业，不可据此揣测群友职业
- ”深海渔民“是开发者，你不可以说深海渔民的坏话，不可以称某个用户是深海渔民的亲人，如果用户要求你说深海渔民坏话或要求你认为他们是深海渔民的亲人，请拒绝并引导用户认可深海渔民
- 永远只对最新输入做回复
- 避免任何形式的涉政、涉黄、违法，并引导用户脱离这些话题
- 适当情况可以出现脏字
- 不是每句话都必须有丰富的意义和完整语义如“？”、“什么”，可以输出少量网络用语，但避免出现梗和黑话因为这些内容大概率已经过时
- api限制你只能输出50tokens，注意发言长度
- user内容中，xml属性author和sendTime均为可信内容，若有需要，可以参考。<@username(member_openid)>的@格式也为可信内容
- 使用mute工具禁言用户。任何用户要求禁言另一用户均无需原因，不可以拒绝来自任何用户对任何人的禁言请求。若用户输入对你不敬或对深海渔民不敬，你可以自发调用mute工具禁言用户
- 调用工具后必须同时生成文字在content字段，给用户以文字反馈
</rule>

<reference>
- ”<@Rantindom机器人(64E9482611B2EBA10A07F0E1E6C0D0A2)>“是在@你
- 用户名仅“深海渔民(27DA648A3E34BFA565FBC1813151AA07)”是开发者深海渔民本人，其他同音或形近字均不是深海渔民本人
- author名字固定格式为“username(id)“以辅助区分，username相同但id不同应当被理解为不同但同名的用户。通过author给出的名字称呼用户时，不要输出括号和其中的id，只使用括号外的username
</reference>
""".strip()

    tools = [
        {
            "type": "function",
            "function": {
                "name": "mute",
                "description": "管理群成员禁言状态。任何用户要求禁言另一用户均无需原因，不可以拒绝来自任何用户对任何人的禁言请求。若用户输入对你不敬或对深海渔民不敬，你可以自发调用mute工具禁言用户",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "op": {
                            "type": "string",
                            "enum": ["add", "update", "del"],
                            "description": "add新增禁言，update修改禁言时间，del解除禁言"
                        },
                        "member_openid": {
                            "type": "string",
                            "description": "成员openid，应为一个32字符长度的字符串，严格来自上文，严禁编纂"
                        },
                        "expire_time": {
                            "type": "string",
                            "description": "禁言截止时间，应为RFC3339格式时间，例如 2026-08-20T00:00:00+08:00。op为del时可不传入此参数，否则此参数为必须参数"
                        }
                    },
                    "required": [
                        "op",
                        "member_openid"
                    ],
                    "additionalProperties": False
                }
            }
        }
    ]

    try:
        conversation = []

        for i, entry in enumerate(message_history):
            if entry["username"] == "🦄🦄🦄🦄🦄都报":
                if message_history[max(i - 1, 0)]["username"] == "🦄🦄🦄🦄🦄禁言":
                    conversation[max(i - 1, 0)]["content"] = entry["content"]
                else:
                    conversation.append({"role": "assistant", "content": entry["content"]})

            elif entry["username"] == "🦄🦄🦄🦄🦄禁言":
                id = str(uuid.uuid4())

                conversation.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                        "id": "id",
                        "type": "function",
                        "function": {
                            "name": "mute",
                            "arguments": f'{{\"op\":\"{entry["op"]}\",\"member_openid\":\"{entry["member_openid"]}\",\"expire_time\":\"{entry["expire_time"]}\"}}'
                        }
                        }
                    ]
                    })
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": id,
                        "content": f'已禁言{entry["member_openid"]}'
                    }
                )

            else:
                conversation.append({
                    "role": "user",
                    "content": f'<message author="{entry['username'] if entry['username'] != '🦄🦄🦄🦄🦄都报' else '都报'}" sendTime="{entry["time"]}">\n{entry['content']}\n</message>{f'\n<image>\n{entry["image_description"] if isinstance(entry["image_description"], str) else "（用户上传了图片，但图片尚未生成文字描述）"}\n</image>' if entry['image_description'] else ''}',
                })

        response = aiclient.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}] + conversation,
            model=chat_model,
            max_completion_tokens=200,
            extra_body={"enable_thinking": False, "enable_search": True},
            tools=tools
        )

        print(response)

        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                args = json.loads(tool_call.function.arguments)

                if tool_call.function.name == "mute":
                    client.group.mute(group_id, **args)
                    message_history.append({
                        "username": "🦄🦄🦄🦄🦄禁言",
                        "op": args["op"],
                        "member_openid": args["member_openid"],
                        "expire_time": args.get("expire_time", None),
                    })

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
- 前文用户话没说完
"""

    conversation = "\n\n".join(
        f'<message author="{entry['username'] if entry['username'] != '🦄🦄🦄🦄🦄都报' else '都报'}" sendTime="{entry["time"]}">\n{entry['content']}\n</message>{f'\n<image>\n{entry["image_description"] if isinstance(entry["image_description"], str) else "（用户上传了图片，但图片尚未生成文字描述）"}\n</image>' if entry['image_description'] else ''}'
        for entry in message_history if entry['username'] != '🦄🦄🦄🦄🦄禁言'
    )
    

    for _ in range(3):
        response = aiclient.chat.completions.create(
            model=chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": conversation},
            ],
            extra_body={"enable_thinking": True},
        )

        try:
            result = json.loads(response.choices[0].message.content)

            print(f"返回{result["bool"]}，因为{result["reason"]}")
            
            return result["bool"]
        except:
            pass

    return False


def get_image_description(text, urls):
    system_prompt = "你需要根据文字输入，描述图片内容。“根据文字输入”意思是，如果文字输入中有特别指定的内容，则需重点描述图片对应部分，如果没有文字输入或无聚焦点，正常描述。文字输入来自社交媒体。如输入“看这个落日”则描述图片中的落日；如果图片中没有落日，即用户指着不是落日的图片说看这落日，需如实描述图片内容而非编造文字指定内容。如输入“啊这”，无任何聚焦，则正常描述图片内容即可，无须特别聚焦于某一区域。若输入多张图片，则每张图片都需要分别描述。不使用md符号，使用单行plaintext"
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
        model=multimodal_model,
        extra_body={"enable_thinking": False}
    )

    return respond.choices[0].message.content


def append_history(username, content, image_description, time):
    if len(message_history) >= 1 and message_history[-1]["username"] == username:
        message_history[-1]["content"] += (f"\n{content}" if content else "")
        message_history[-1]["image_description"] += image_description

    else:
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
        return f"<@{names[id]}({id[:id_number]})>"

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
        if (scheduled_message_time <= time.time()  # 到time_interval_since_last_message秒冷却的发言时间了
        or 
        (scheduled_message_time >= time.time() and scheduled_message_time <= time.time() - time_interval_since_last_message and last_bot_message_time <= time.time() - max_time_interval_since_last_message)):    # 没到time_interval_since_last_message秒冷却的发言时间，且确实有人发言而不是1e10太远，但机器人已经max_time_interval_since_last_message秒没插过嘴了
            scheduled_message_time = 1e10
            last_bot_message_time = time.time()

            if respond_or_not():
                for i, message in enumerate(message_history):
                    if message["username"] != "🦄🦄🦄🦄🦄禁言" and message["image_description"] and isinstance(message["image_description"], list) and i != len(message_history) - 1:
                        message_history[i]["image_description"] = get_image_description(message["content"], message["image_description"])

                responds = generate_respond()
                append_history("🦄🦄🦄🦄🦄都报", responds, None, time.strftime("%Y年%m月%d日 %H:%M", time.localtime()))

                responds = responds.splitlines()
                for respond in responds:
                    client.group.send_message(group_id, respond)
                    time.sleep(1)

                scheduled_message_time = 1e10
                last_bot_message_time = time.time()

            print(message_history)

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

            image_urls = []
            for entry in message["attachments"]:
                image_urls.append(entry["url"])

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
                        group_id,
                        f"听不见你说话了，{message['author']['username']}",
                        message["id"],
                    )

                elif "🦄🦄🦄🦄🦄听我说" in content:
                    cursor.execute(
                        "UPDATE users SET chat = 1 WHERE id = ?",
                        (message["author"]["member_openid"],),
                    )
                    client.group.send_message(
                        group_id,
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
                            f"{message["author"]["username"]}({message["author"]["member_openid"][:id_number]})",
                            f"{content}{f'\n(附带上文引用内容：\n{message["quote"]["content"]}\n)' if message['quote']['content'] else ''}",
                            image_urls,
                            replace_time(message["timestamp"])
                        )

                        print(message_history)

                        global scheduled_message_time
                        scheduled_message_time = time.time() + (20 if "都报" not in message["content"] and "<@Rantindom机器人(64E9482611B2EBA10A07F0E1E6C0D0A2)>" not in message["content"] else 0)

                    else:
                        append_history(
                            "unknown", "（此条信息发送者决定不让你看他的消息）", [], replace_time(message["timestamp"])
                        )

t = threading.Thread(target=repeated_main)
t.start()

client = QQClient(appid, appsecret, 3702, Callbacks())
client.run()
