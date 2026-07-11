import requests
import json
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, Request
import openai

app = FastAPI()

group_id={
    "26EB43931720954A79D89989C3B29278": "开发者团队群",
    "27A9F65E088E6559792350DFA96C2326": "测试者群",
    "95B974CA59C598B7F4088290C3EA7DC9": "交流1群",
    "0E0F9F8E6084342A0819481474E2D312": "交流2群"
}
 
#机器人配置
qq_number="3889624799"
appid="***REMOVED***"
token="RFOFsu87pn7d5CANmcaI4v0EzLzmBPg7"
appsecret="***REMOVED***"

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
- 不要在输出内容前加“都报：”声明身份，输入内容中“都报（你自己）：”不需要模仿
- 句末不要输出句号
- 输入格式为多行的“名字: 内容“，名字均为网名，不代表群友职业，不可揣测群友职业
</rule>

<reference>
- 消息中的“<@64E9482611B2EBA10A07F0E1E6C0D0A2>”是发言者在@你
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
    

@app.post('/')
async def main(request: Request):
    payload = await request.json()
    op = payload["op"]
    d = payload["d"]
    id = payload["id"]
    t = payload["t"]

    if id in previous_message_id:
        return 0
    else:
        previous_message_id.append(id)

    match op:
        case 0:
            if t == "C2C_MESSAGE_CREATE" and d["author"]["user_openid"] == "27DA648A3E34BFA565FBC1813151AA07":
                print(d)
                print(f"收到私信: {d["content"]}")
                send_to_group("95B974CA59C598B7F4088290C3EA7DC9", d["content"])
                return 0

            elif t == "GROUP_MESSAGE_CREATE" and d["group_id"] == "95B974CA59C598B7F4088290C3EA7DC9":
                print(f"{d["author"]["username"]}: {d["content"]}{f"\n(附带上文引用内容：\n{d["parallel_message"]["msg_nodes"][0]["content"]}\n)" if "parallel_message" in d else ""}")
                append_history(f"{d["author"]["username"]}: {d["content"]}{f"\n(附带上文引用内容：\n{d["parallel_message"]["msg_nodes"][0]["content"]}\n)" if "parallel_message" in d else ""}")
                send_to_group("95B974CA59C598B7F4088290C3EA7DC9", generate_respond())

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
            response = generate_signature(d)

            return response