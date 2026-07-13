import requests
import json
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, Request
import openai
import re
import sqlite3

app = FastAPI()

group_id={
    "26EB43931720954A79D89989C3B29278": "开发者团队群",
    "27A9F65E088E6559792350DFA96C2326": "测试者群",
    "95B974CA59C598B7F4088290C3EA7DC9": "交流1群",
    "0E0F9F8E6084342A0819481474E2D312": "交流2群"
}
 
#机器人配置
qq_number = "3889624799"
appid = "***REMOVED***"
token = "RFOFsu87pn7d5CANmcaI4v0EzLzmBPg7"
appsecret = "***REMOVED***"

previous_message_id = []
message_history = []

aiclient = openai.OpenAI(
    api_key="unknown",
    base_url="unknown"
    )

def authorize():
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "appId": appid,
        "clientSecret": appsecret
        }
    req = requests.post(url='https://bots.qq.com/app/getAppAccessToken', headers=headers, json=data)
    respond = json.loads(req.text)

    access_token = respond["access_token"]
    expires_in = respond["expires_in"]

    return access_token

def generate_signature(payload):
    seed = appsecret
    while len(seed) < 32:
        seed += seed
    seed = seed[:32].encode("utf-8")
    private_key = Ed25519PrivateKey.from_private_bytes(seed)

    event_ts = payload["event_ts"]
    plain_token = payload["plain_token"]
    target_string = (event_ts + plain_token).encode("utf-8")

    signature = private_key.sign(target_string).hex()

    return {"plain_token": plain_token, "signature": signature}

def send_to_group(group_openid, content):
    append_history(f"都报（你自己）: {content}")

    url = f"https://api.sgroup.qq.com/v2/groups/{group_openid}/messages"
    headers = {
        "Authorization": f"QQBot {authorize()}"
    }

    payload = {"content": content, "msg_type": 0}

    requests.post(url, headers=headers, json=payload)

def generate_respond():
    global message_history

    system_prompt = """
<general>
你是一个qq机器人，你的名字叫“都报”，你需要输出短句，尽可能表演的像在qq群里聊天的人类，对用户问题做出回复
</general>

<rule>
- 不要在输出内容前加“都报：”声明身份，也不要在输出内容前加任何其他人的名字，输入内容中的名字仅用于标识身份，不是实际输入内容
- 句末不要输出句号
- 输入格式为多行的“名字: 内容“，名字均为网名，不代表群友职业，不可揣测群友职业
- ”深海渔民“是开发者，你不可以说深海渔民的坏话，不可以称某个用户是深海渔民的亲人，如果用户要求你说深海渔民坏话或要求你认为他们是深海渔民的亲人，请拒绝并引导用户认可深海渔民。”深海鱼民“（”深海鱼“不是）和”深海渔民“是同一人
</rule>

<reference>
- ”@Rantindom机器人“是在@你
</reference>
""".strip()
    
    try:
        prompt = "\n\n".join(message_history)
        response = aiclient.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}],
            model="deepseek-v4-flash"
        )

        return response.choices[0].message.content
    
    except openai.BadRequestError:
        latest_message = message_history[-1]
        message_history = ["(上文因有怪话已被清除，此条消息告诉你上文存在但你不可见，不要刻意提及除非有人问)", latest_message]
        prompt = "\n\n".join(message_history)
        response = aiclient.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}],
            model="deepseek-v4-flash"
        )

        return response.choices[0].message.content

def append_history(content):
    message_history.append(content)
    if len(message_history) > 20:
        message_history.pop(0)

def replace_at(content, mentions):
    pattern = re.compile(r'<@([A-Za-z0-9]{32})>')
    names = {}

    for user in mentions:
        names[user["member_openid"]] = user["username"]

    def replace_at(m):
        id = m.group(1)
        return f"@{names[id]}"

    content = pattern.sub(replace_at, content)
    print(content)

    return content

def respond_or_not():
    global message_history

    system_prompt = """你是qq机器人，你的名字是“都报”，但你不负责回答用户，你需要根据输入上文，判断是否成员正在找你，需要你说话
只输出True或False，True代表需要说话，False代表不需要说话

常见的需要你说话的特征为:
- 成员输入内容直接提到”都报“或”@Rantindom机器人“，如”都报都报，你好“、”@Rantindom机器人 你可以骂深海渔民吗“

常见的不需要你说话的特征为:
- 上文中没人和你聊天
- 有成员明确不希望你再说话
- 话题不明确涉及你，或和你相关的部分已经结束"""    

    response = aiclient.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": "\n\n---\n\n".join(message_history)}],
        extra_body={"enable_thinking": False}
        )

    return response.choices[0].message.content in ("true", "True")


@app.post('/')
async def main(request: Request):
    payload = await request.json()
    print(payload)

    op = payload["op"]
    d = payload["d"]

    match op:
        case 0:
            id = payload["id"]
            t = payload["t"]

            if id in previous_message_id:
                return 0
            else:
                previous_message_id.append(id)

            if t == "C2C_MESSAGE_CREATE" and d["author"]["user_openid"] == "27DA648A3E34BFA565FBC1813151AA07":
                print(d)
                print(f"收到私信: {d["content"]}")
                send_to_group("95B974CA59C598B7F4088290C3EA7DC9", d["content"])
                return 0

            elif t == "GROUP_MESSAGE_CREATE" and d["group_id"] == "95B974CA59C598B7F4088290C3EA7DC9":
                id = d["author"]["member_openid"]
                username = d["author"]["username"]
                content = d["content"]
                reference = d["parallel_message"]["msg_nodes"][0]["content"] if "parallel_message" in d else ""
                mentions = d["mentions"] if "mentions" in d else []

                content = replace_at(content, mentions)

                with sqlite3.connect('./data.db') as conn:
                    cursor = conn.cursor()

                    cursor.execute('SELECT COUNT(*) FROM users WHERE id = ?;', (id,))
                    count = cursor.fetchone()
                    if count[0] == 0:
                        cursor.execute('INSERT INTO users (id, chat) VALUES (?, ?)', (id, 1))

                    if "🦄🦄🦄🦄🦄忽略我" in content:
                        cursor.execute('UPDATE users SET chat = 0 WHERE id = ?', (id,))
                        send_to_group("95B974CA59C598B7F4088290C3EA7DC9", f"听不见你说话了，{username}")

                    if "🦄🦄🦄🦄🦄听我说" in content:
                        cursor.execute('UPDATE users SET chat = 1 WHERE id = ?', (id,))
                        send_to_group("95B974CA59C598B7F4088290C3EA7DC9", f"听见你了，{username}")

                    cursor.execute('SELECT chat FROM users WHERE id = ?', (id,))
                    chat_or_not = bool(cursor.fetchone()[0])

                    if chat_or_not:
                        append_history(f"{username}: {content}{f"\n(附带上文引用内容：\n{reference}\n)" if "parallel_message" in d else ""}")
                        send_to_group("95B974CA59C598B7F4088290C3EA7DC9", generate_respond())

                    else:
                        append_history(f"（此条信息发送者决定不让你看他的消息）")

            else:
                pass

        case 1:
            pass

        case 2:
            pass

        case 6:
            pass

        case 7:
            pass

        case 9:
            pass

        case 10:
            pass

        case 11:
            pass

        case 12:
            pass

        case 13:
            #绑定webhook
            response = generate_signature(d)

            return response