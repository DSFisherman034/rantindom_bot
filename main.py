import botpy
from botpy.message import GroupMessage
from openai import OpenAI
import time
import json
import random
import jwt
import requests
import re
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

#别名
true=True
false=False

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

aiclient = OpenAI(
    api_key="sk-f131f3620a2347c08e183e6331a9633b",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
model = SentenceTransformer('/bot/text2vec-base-chinese', local_files_only=True)

INDEX_MC_PATH = "/bot/wiki_mc.index"  # 你的mc wiki索引文件路径
index_mc = faiss.read_index(INDEX_MC_PATH)
META_MC_PATH = "/bot/wiki_meta_mc.json"
with open(META_MC_PATH, "r", encoding="utf-8") as f:
    metadata_mc = json.load(f)

def game(choice,player):
    with open('./coin.txt','r',encoding="utf-8") as coin_file:
        coin=json.loads(coin_file.read().strip())
        if not player in coin:
            coin[player]=0
        if coin[player] < 5:
            respond=f"\n[❌]你只剩{coin[player]}金币了，无法参与石头剪刀布，石头剪刀布需要5金币入场费"
        else:
            coin[player]-=5
            coin[player]=round(coin[player],2)
            choices={1:"石头",2:"剪刀",3:"布"}
            bot_choice=random.randint(1,3)
            if choice == bot_choice:
                coin[player]+=5
                respond=f"\n[💸]你交出了5金币入场费\n[⭕️]你出了{choices[choice]}，我出了{choices[bot_choice]}，平局\n[📄]入场费已退回"
            elif choice == bot_choice-1 or choice == bot_choice+2:
                coin_get=round(random.uniform(9,11),2)
                coin[player]+=coin_get
                with open('./xp.txt','r',encoding="utf-8") as file1:
                    xp=json.loads(file1.read().strip())
                    xp[player]+=1
                    respond=f"\n[💸]你交出了5金币入场费\n[✅]你出了{choices[choice]}，我出了{choices[bot_choice]}，你赢了\n[💵]你因此获得了1点经验值和{coin_get}个金币\n[📄]当前经验值：{xp[player]}\n[📄]当前金币：{coin[player]}"
                    with open('./xp.txt','w',encoding="utf-8") as file2:
                        file2.seek(0)
                        xp=str(xp).replace("'",'"')
                        file2.write(xp)
            else:
                respond=f"\n[💸]你交出了5金币入场费\n[❌]你出了{choices[choice]}，我出了{choices[bot_choice]}，你输了\n[💸]入场费没有退回\n[📄]当前金币：{coin[player]}"
            with open('./coin.txt','w',encoding="utf-8") as coin_file1:
                coin = str(coin).replace("'", '"')
                coin_file1.write(str(coin))
    return respond

class MyClient(botpy.Client):
    async def on_group_at_message_create(self, message: GroupMessage):  #q群@机器人
        content=""
        with open('./player_list.txt','r') as file:
            list=json.loads(file.read().strip())
            if not message.author.member_openid in list:    #如果没绑定

                if message.content == " /绑定 " or message.content == " /绑定" or message.content == " 绑定":
                    content=f"\n[❌]您似乎忘记了输入游戏名，请@我并输入“绑定 你的游戏名”绑定信息"
                    
                elif (match := re.match(r'^[\s/]*绑定\s+([^\s]+)(?:\s+(确认))?\s*$', message.content)):
                    if match.group(2) == "确认":
                        with open('./player_list.txt','r+') as file1:
                            list=json.loads(file1.read().strip())
                            list[message.author.member_openid]=match.group(1)
                            file1.seek(0)
                            list = str(list).replace("'", '"')
                            file1.write(str(list))
                            content=f"\n[✅]绑定游戏名“{match.group(1)}”成功"
                    else:
                        content=f"\n[⭕️]您确定要绑定游戏名“{match.group(1)}”吗\n如确定请@我并输入“/绑定 {match.group(1)} 确认“\n游戏名有误会影响游戏内道具发放，请反复确认"

                else:
                    content=f"\n[❌]您还未绑定游戏名信息，请@我并输入“绑定 你的游戏名”绑定信息"
            else:   #如果绑定了
                if (match := re.match(r'^\s*$', message.content)):
                    content=f"\n你好我是Rantindom机器人，尝试@我输入“菜单”或任意内容开始聊天吧🥰"

                elif message.content == ' 强制闲聊':
                    content=f"\n[✅]已开启强制闲聊：接下来不论你的问题与wiki是否相关都只视为与机器人闲聊"
                    with open('./chated.txt','r',encoding="utf-8") as file1:
                        chated=json.loads(file1.read().strip())
                        chated[message.author.member_openid]=0
                        with open('./chated.txt','w',encoding="utf-8") as file2:
                            file2.seek(0)
                            chated = str(chated).replace("'", '"')
                            file2.write(str(chated))
                            
                elif message.content == ' 不强制闲聊':
                    content=f"\n[✅]已关闭强制闲聊：接下来若你的问题与Rantindom相关则自动检索wiki内容给予你回答，同时默认你同意我们收集你在与wiki检索模式的机器人的对话数据"
                    with open('./chated.txt','r',encoding="utf-8") as file1:
                        chated=json.loads(file1.read().strip())
                        chated[message.author.member_openid]=1
                        with open('./chated.txt','w',encoding="utf-8") as file2:
                            file2.seek(0)
                            chated = str(chated).replace("'", '"')
                            file2.write(str(chated))
                    
                elif (match := re.match(r'^[\s/]*输出\s+(.*)$', message.content)) and message.author.member_openid == "27DA648A3E34BFA565FBC1813151AA07":
                    content=f"\n[🗣️]{match.group(1)}\n-内容来自深海渔民"

                elif (match := re.match(r'^[\s/]?喇叭\b(?:$|\s+(.*))$', message.content)):
                    if match.group(1) == None:
                        with open('./chat_history.txt','r+',encoding="utf-8") as file1:
                            laba_history=json.loads(file1.read().strip())
                            if laba_history["total"] > laba_history[message.group_openid]:
                                content=""
                                while laba_history["total"] > laba_history[message.group_openid]:
                                    laba_history[message.group_openid]+=1
                                    content+=f"\n{laba_history[str(laba_history[message.group_openid])]}"
                                file1.seek(0)
                                laba_history=str(laba_history).replace("'",'"')
                                file1.write(str(laba_history))
                            else:
                                content="\n[❌]已发送完毕，没有新的喇叭了"
                        content+=f"\n[📄]若要发送喇叭请@我并输入“喇叭 内容”，发送喇叭需要扣除100金币"
                    else:
                        with open('./coin.txt','r',encoding="utf-8") as coin_file:
                            coin=json.loads(coin_file.read().strip())
                            if not message.author.member_openid in coin:
                                coin[message.author.member_openid]=0
                            if coin[message.author.member_openid] < 100:
                                content=f"\n[❌]你只剩{coin[message.author.member_openid]}金币了，无法发送喇叭，发送喇叭需要100金币"
                            else:
                                coin[message.author.member_openid]-=100
                                coin[message.author.member_openid]=round(coin[message.author.member_openid],2)
                                with open('./chat_history.txt','r+',encoding="utf-8") as file1:
                                    laba_content=json.loads(file1.read().strip())
                                    laba_content["total"]+=1
                                    laba_content[str(laba_content["total"])]=f"[📄]{match.group(1)}\n-来自{group_id[message.group_openid]}-{time.strftime("%Y年%m月%d日%H:%M:%S",time.localtime())}"
                                    file1.seek(0)
                                    laba_content=str(laba_content).replace("'",'"')
                                    file1.write(str(laba_content))
                                    content=f"\n[✅]已扣除100金币，已发送喇叭: {match.group(1)}\n[📄]剩余金币：{coin[message.author.member_openid]}"
                                    with open('./coin.txt','w',encoding="utf-8") as coin_file1:
                                        coin_file1.seek(0)
                                        coin = str(coin).replace("'", '"')
                                        coin_file1.write(str(coin))
                
                elif (match := re.match(r'^[\s/]*查单词\s+(.*)$', message.content)):
                    word=match.group(1)
                    if word =="rantindom" or word == "Rantindom":
                        content=f"\n[📄]单词{word}不在英文语境中有含义，但{word}是我们服务器的名字"
                    else:
                        messages=[
                            {"role":"system","content":'Check spelling: if correct, output {"check":"True","mean":"definition"}; if wrong, {"check":"False","guess":"your_guess","mean":"definition_of_the_word_you_guess"}.Example：apple→{"check":"True","mean":"n.苹果"}, appla→{"check":"False","guess":"apple","mean":"n.苹果"},if word is rantindom→{"check":"True","mean":"n.一个Minecraft服务器"}'},
                            {"role": "user", "content": word}
                            ]
                        response = aiclient.chat.completions.create(
                            model="qwen-max",
                            messages=messages
                        )
                        response=json.loads(response.choices[0].message.content)
                        if response["check"] == "True":
                            content=f"\n[📄]单词{word}的意思是{response['mean']}"
                        else:
                            content=f"\n[❌]单词{word}拼写错误，猜你想查的是{response['guess']}，意思是{response['mean']}"
                    
                elif (match := re.match(r'^[\s/]*记账\s+(.*)$', message.content)) and message.author.member_openid == "27DA648A3E34BFA565FBC1813151AA07":
                    with open('./cost.txt','r',encoding='utf-8') as file1:
                        cost=int(file1.read().strip())
                        cost+=int(match.group(1))
                        with open('./cost.txt','w',encoding='utf-8') as file2:
                            file2.write(str(cost))
                        content=f"\n[📄]已记账{match.group(1)}元，当前总成本：{cost}元"

                elif (match := re.match(r'^[\s/]*天气\s+(.*)$', message.content)):
                    with open('./weather.txt','r',encoding="utf-8") as file1:
                        weather=int(file1.read().strip())
                        if weather >=2:
                            private_key='''-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIHyhlR6ICYRje4xZemtWHJP/NipJ/kquolp/SmUFxx7s
-----END PRIVATE KEY-----'''
                            headers={"alg": "EdDSA","kid": "KH59Q3D5BC"}
                            payload={"sub": "498A4N6MFU","iat": int(time.time())-30,"exp": int(time.time())+60}
                            encode_jwt= {"Authorization": f"Bearer {jwt.encode(payload, private_key, algorithm='EdDSA', headers = headers)}", "number":"1", "lang":"zh"}
                            location=match.group(1)
                            params={"location": location}
                            url='https://geoapi.qweather.com/v2/city/lookup'
                            response = requests.get(url, headers=encode_jwt, params=params)
                            response=response.json()
                            if "error" in response:
                                weather-=1
                                content=f"\n[❌]未找到{location}，请检查城市是否在中国或是否有错别字\n查询天气剩余额度：{weather}"
                            else:
                                location=f"{response['location'][0]['adm1']}.{response['location'][0]['adm2']}.{response['location'][0]['name']}"
                                messages=[
                                {"role":"system","content":'处理用户输入的层级式行政区划文本（如A.B.C），按规则简化：同级重复则合并。直辖市/省同名时保留最高级。添加对应行政后缀，例：北京.北京.北京→北京；甘肃.兰州.兰州→甘肃省兰州市。只输出简化后的行政区划文本，不要添加其他的字'},
                                {"role": "user", "content": location}
                                ]
                                ai_response = aiclient.chat.completions.create(
                                model="qwen-max",
                                messages=messages
                                )
                                location=ai_response.choices[0].message.content
                                if response["location"][0]["country"] != "中国":
                                    location=response["location"][0]["country"]+" "+location
                                weather-=2
                                url='https://devapi.qweather.com/v7/weather/now'
                                params={"location": response["location"][0]["id"], "lang":"zh","unit":"m"}
                                response1 = requests.get(url, headers=encode_jwt, params=params)
                                response1 = response1.json()
                                content=f"\n[📄]城市：{location}\n[📄]天气：{response1["now"]["text"]}\n[📄]温度：{response1["now"]["temp"]}摄氏度（体感{response1["now"]["feelsLike"]}摄氏度）\n[📄]湿度：{response1["now"]["humidity"]}%\n[📄]气压：{response1["now"]["pressure"]}hPa\n[📄]能见度：{response1["now"]["vis"]}km\n[📄]数据来自和风天气，观测时间{response1["now"]["obsTime"]}\n[📄]查询天气剩余额度：{weather}"
                            with open('./weather.txt','w',encoding="utf-8") as file2:
                                file2.write(str(weather))
                        else:
                            content=f"\n[❌]查询天气额度已用完，请明天再尝试"

                elif re.match(r'^[\s/]?绑定\b(?:$|\s+(.*))$', message.content):
                    with open('./player_list.txt','r') as file1:
                        list=json.loads(file1.read().strip())
                        if message.author.member_openid in list:
                            content=f"\n[❌]你已经绑定过信息了，您的游戏名是{list[message.author.member_openid]}"
                        
                elif message.content == " /我的信息 " or message.content == " /我的信息" or message.content == " 我的信息":
                    with open('./coin.txt','r',encoding="utf-8") as coin_file, open('./xp.txt','r',encoding="utf-8") as file1, open('./lv.txt','r',encoding="utf-8") as file2:
                        coin=json.loads(coin_file.read().strip())
                        xp=json.loads(file1.read().strip())
                        lv=json.loads(file2.read().strip())
                        if not message.author.member_openid in xp:
                            xp[message.author.member_openid]=0
                        if not message.author.member_openid in lv:
                            lv[message.author.member_openid]=1
                        if not message.author.member_openid in coin:
                            coin[message.author.member_openid]=0
                        content=f"\n[📄]游戏名：{list[message.author.member_openid]}\n[📄]等级：{lv[message.author.member_openid]}\n[📄]经验值：{xp[message.author.member_openid]}/{10*lv[message.author.member_openid]}\n[📄]金币：{coin[message.author.member_openid]}"
                                    
                elif (match := re.match(r'^[\s/]?石头剪刀布\b(?:$|\s+(.*))$', message.content)):
                    if message.content == " /石头剪刀布 " or message.content == " /石头剪刀布" or message.content == " 石头剪刀布":
                        content="\n[📄]欢迎游玩石头剪刀布\n[📄]游戏规则：与常规石头剪刀布一致，即石头克剪刀，剪刀克布，布克石头\n[💸]入场费：5金币\n[💵]奖励：若输掉了游戏则5金币入场费不予退回，若赢得游戏则获得随机9到11金币和1点经验值，若平局则退回5金币入场费并不给予额外金币和额外经验值"
                    elif message.content == " /石头剪刀布 石头" or message.content == " /石头剪刀布 石头" or message.content == " 石头剪刀布 石头":
                        content=game(1,message.author.member_openid)
                    elif message.content == " /石头剪刀布 剪刀" or message.content == " /石头剪刀布 剪刀" or message.content == " 石头剪刀布 剪刀":
                        content=game(2,message.author.member_openid)
                    elif message.content == " /石头剪刀布 布" or message.content == " /石头剪刀布 布" or message.content == " 石头剪刀布 布":
                        content=game(3,message.author.member_openid)
                    else:
                        content=f"\n[❌]没有理解你要出什么，请检查输入"

                elif message.content == " /服务器 " or message.content == " /服务器" or message.content == " 服务器":
                    current=time.time()
                    time1=current-1613059200    #项目时间，距离2021/2/12
                    day1=int(time1/86400)
                    time2=current-1705593600    #魔幻城时间，距离2024/1/19
                    day2=int(time2/86400)
                    time3=current-1724515200    #缚魂人时间，距离2024/8/25
                    day3=int(time3/86400)
                    with open('./cost.txt','r',encoding="utf-8") as file1:
                        cost=file1.read().strip()
                    content=f"\n[📄]当前服务器：Rantindom:缚魂人\n[📄]服号：81238313\n[📄]开服时间：Rantindom项目创立于2021/2/12，距今{day1}天\n魔幻城复刻存档于2024/1/19开始开发，距今{day2}天\n缚魂人服务器于2024/8/25开始开发，距今{day3}天\n[📄]总成本：{cost}元"

                elif message.content == " /菜单 " or message.content == " /菜单" or message.content == " 菜单":
                    if message.group_openid == "26EB43931720954A79D89989C3B29278":#开发者群
                        content=f"\n[📄]Rantindom机器人通用指令菜单\n[🚩]<任意内容>\n  -聊天\n\n[🚩]强制闲聊\n -输入<任意内容>都将使用闲聊模式\n\n[🚩]不强制闲聊\n -若输入内容与Rantindom wiki相关，则机器人根据wiki内容给予回复，回复内容和问题将被记录用于机器人微调\n\n[🚩]mc <任意内容>\n -机器人根据mc wiki（zh.minecraft.wiki）给予回复，当前只支持指令相关\n\n[🚩]绑定 [游戏名] [确认]\n  -绑定游戏名\n\n[🚩]喇叭 [内容]\n  -在rtd所有群内发送喇叭\n   输入内容则扣除100金币发送喇叭，不输入内容则查看所有此群未查看的喇叭\n\n[🚩]查单词 <单词>\n  -查询一个单词，可能在后期修改为单词接龙游戏\n\n[🚩]天气 <城市>\n  -查询一个地点的天气\n\n[🚩]/我的信息(指令列表)\n  -查询账号信息\n\n[🚩]石头剪刀布 [石头/剪刀/布]\n  -玩一把纯随机的石头剪刀布\n   不输入参数以查看游戏规则\n\n[🚩]/服务器(指令列表)\n  -查看服务器相关信息\n\n[🚩]/签到(指令列表)\n  -每日签到\n\n[🚩]发病 <内容>\n  -生成一段关于“内容”的“你说的对，但是...“发病文案\n\n[🚩]版本\n  -查看近期服务器更新日志\n\n----------\n[💻]Rantindom机器人开发指令菜单\n[🚩]待办 [完成/添加/删除/全部] [id]\n  -查看或操作待办列表\n\n[🚩]版本 发布 v1.2:abc\n  版本 修改 v1.2 abcdef\n  -发布新版本和修改版本更新内容"
                    elif message.group_openid == "27A9F65E088E6559792350DFA96C2326":#测试者群
                        content=f"\n[📄]Rantindom机器人通用指令菜单\n[🚩]<任意内容>\n  -聊天\n\n[🚩]强制闲聊\n -输入<任意内容>都将使用闲聊模式\n\n[🚩]不强制闲聊\n -若输入内容与Rantindom wiki相关，则机器人根据wiki内容给予回复，回复内容和问题将被记录用于机器人微调\n\n[🚩]mc <任意内容>\n -机器人根据mc wiki（zh.minecraft.wiki）给予回复，当前只支持指令相关\n\n[🚩]绑定 [游戏名] [确认]\n  -绑定游戏名\n\n[🚩]喇叭 [内容]\n  -在rtd所有群内发送喇叭\n   输入内容则扣除100金币发送喇叭，不输入内容则查看所有此群未查看的喇叭\n\n[🚩]查单词 <单词>\n  -查询一个单词，可能在后期修改为单词接龙游戏\n\n[🚩]天气 <城市>\n  -查询一个地点的天气\n\n[🚩]/我的信息(指令列表)\n  -查询账号信息\n\n[🚩]石头剪刀布 [石头/剪刀/布]\n  -玩一把纯随机的石头剪刀布\n   不输入参数以查看游戏规则\n\n[🚩]/服务器(指令列表)\n  -查看服务器相关信息\n\n[🚩]/签到(指令列表)\n  -每日签到\n\n[🚩]发病 <内容>\n  -生成一段关于“内容”的“你说的对，但是...“发病文案\n\n[🚩]版本\n  -查看近期服务器更新日志\n\n----------\n[🐞]Rantindom机器人测试指令菜单"
                    else:
                        content=f"\n[📄]Rantindom机器人菜单\n[🚩]<任意内容>\n  -聊天\n\n[🚩]强制闲聊\n -输入<任意内容>都将使用闲聊模式\n\n[🚩]不强制闲聊\n -若输入内容与Rantindom wiki相关，则机器人根据wiki内容给予回复，回复内容和问题将被记录用于机器人微调\n\n[🚩]mc <任意内容>\n -机器人根据mc wiki（zh.minecraft.wiki）给予回复，当前只支持指令相关\n\n[🚩]绑定 [游戏名] [确认]\n  -绑定游戏名\n\n[🚩]喇叭 [内容]\n  -在rtd所有群内发送喇叭\n   输入内容则扣除100金币发送喇叭，不输入内容则查看所有此群未查看的喇叭\n\n[🚩]查单词 <单词>\n  -查询一个单词，可能在后期修改为单词接龙游戏\n\n[🚩]天气 <城市>\n  -查询一个地点的天气\n\n[🚩]/我的信息(指令列表)\n  -查询账号信息\n\n[🚩]石头剪刀布 [石头/剪刀/布]\n  -玩一把纯随机的石头剪刀布\n\n[🚩]/服务器(指令列表)\n  -查看服务器相关信息\n\n[🚩]/签到(指令列表)\n  -每日签到\n\n[🚩]发病 <内容>\n  -生成一段关于“内容”的“你说的对，但是...“发病文案\n\n[🚩]版本\n  -查看近期服务器更新日志"

                elif message.content == " /签到 " or message.content == " /签到" or message.content == " 签到":
                    with open('./check.txt','r+',encoding="utf-8") as file1,open('./check_history.txt','r+',encoding="utf-8") as file2:
                        today=json.loads(file1.read().strip())
                        history=json.loads(file2.read().strip())
                        if not message.author.member_openid in history:   #新人从未签到过
                            history[message.author.member_openid]=0
                        if not message.author.member_openid in today:  #今日未签到
                            today["today_total"]+=1
                            today[message.author.member_openid]=time.strftime("%H:%M:%S",time.localtime())
                            history[message.author.member_openid]+=1
                            with open('./coin.txt','r',encoding="utf-8") as coin_file:
                                coin=json.loads(coin_file.read().strip())
                                if not message.author.member_openid in coin:
                                        coin[message.author.member_openid]=0
                                coin_get=round(random.uniform(5,10),2)
                                coin[message.author.member_openid]+=coin_get
                                coin[message.author.member_openid]=round(coin[message.author.member_openid],2)
                                with open('./coin.txt','w',encoding="utf-8") as coin_file1:
                                    coin = str(coin).replace("'", '"')
                                    coin_file1.write(str(coin))
                            with open('./xp.txt','r',encoding="utf-8") as file3:
                                xp=json.loads(file3.read().strip())
                                if not message.author.member_openid in xp:
                                        xp[message.author.member_openid]=0
                                xp_get=10
                                xp[message.author.member_openid]+=xp_get
                                with open('./xp.txt','w',encoding="utf-8") as file4:
                                    file4.seek(0)
                                    xp = str(xp).replace("'", '"')
                                    file4.write(str(xp))
                            with open('./coin.txt','r',encoding="utf-8") as coin_file,open('./xp.txt','r',encoding="utf-8") as file3:
                                coin=json.loads(coin_file.read().strip())
                                xp=json.loads(file3.read().strip())
                                content=f"\n[✅]签到成功,你是今天第{today["today_total"]}个签到的人\n[📄]你已累计签到{history[message.author.member_openid]}次\n\n[💵]你获得了{xp_get}经验值，获得了{coin_get}个金币\n[📄]当前经验值：{xp[message.author.member_openid]}\n[📄]当前金币：{coin[message.author.member_openid]}"
                        else:   #今日签到过
                            content=f"\n[❌]签到失败，你已经在今天的{today[message.author.member_openid]}签到过了"
                        file1.seek(0)
                        today = str(today).replace("'", '"')
                        file1.write(str(today))
                        file2.seek(0)
                        history = str(history).replace("'", '"')
                        file2.write(str(history))
                        
                elif message.content == " 查看" and message.author.member_openid == "27DA648A3E34BFA565FBC1813151AA07":
                    content=message
                    
                elif (match := re.match(r"[\s/]*待办1(?:[\s]+(添加|完成|删除)(?:[\s]+(.+))?)?", message.content)) and message.group_openid == "26EB43931720954A79D89989C3B29278":
                    if match.group(1) == None:
                        todo_total=0
                        with open('./todo/space/todo.txt','r+',encoding="utf-8") as file1:
                            todo=json.loads(file1.read().strip())
                            for id,project in todo.items():
                                if id != "total" :
                                    todo_total+=1
                                    content+=f"\n[📄]id{id}: {project["content"]}"
                        if content == "":
                            content="\n[❌]没有待办事项了"
                        else:
                            content+=f"\n[💻]总待办数：{todo_total}"
                    elif match.group(1) == "添加":
                        if match.group(2) == None:
                            content="\n[❌]添加什么"
                        else:
                            with open('./todo/space/todo.txt','r+',encoding="utf-8") as file1:
                                todo=json.loads(file1.read().strip())
                                if (new_content := re.match(r'^([^:：]+)[\s]*[:：](.+)$', match.group(2))):
                                    
                                    title=new_content.group(1)
                                    todo_content=new_content.group(2)

                                else:
                                    messages=[
                                        {"role":"system","content":'为用户待办生成标题，只输出标题不要加别的内容'},
                                    {"role": "user", "content": match.group(2)}
                                    ]
                                    response = aiclient.chat.completions.create(
                                    model="qwen-max",
                                    messages=messages
                                    )
                                    title=response.choices[0].message.content
                                    todo_content=match.group(2)
                                    
                                todo["total"]=int(todo["total"])+1
                                todo[str(todo["total"])]={"content":title+': '+todo_content}
                                
                                content=f"\n[✅]已添加待办事项：id{todo['total']}: {title}: {todo_content}"
                                file1.seek(0)
                                todo = str(todo).replace("'", '"')
                                file1.write(str(todo))
                    elif match.group(1) == "完成":
                        if "," in match.group(2) or "，" in match.group(2):
                            ids=match.group(2).replace("，",",")
                            ids=ids.split(",")
                            for id in ids:
                                with open('./todo/space/todo.txt','r',encoding="utf-8") as file1:
                                    todo=json.loads(file1.read().strip())
                                    
                                    if str(id) in todo:
                                        content+=f"\n[✅]已完成待办事项：id{id}:{todo[str(id)]["content"]}"
                                        
                                    else:
                                        content+=f"\n[❌]没有找到待办事项：id{id}"
                                    with open('./todo/space/todo.txt','w',encoding="utf-8") as file2:
                                        file2.seek(0)
                                        todo = str(todo).replace("'", '"')
                                        file2.write(str(todo))
                        else:
                            id=match.group(2)
                            with open('./todo/space/todo.txt','r',encoding="utf-8") as file1:
                                    todo=json.loads(file1.read().strip())
                                    if str(id) in todo:
                                        content=f"\n[✅]已完成待办事项：id{id}:{todo[str(id)]["content"]}"
                                    else:
                                        content=f"\n[❌]没有找到待办事项：id{id}"
                                    with open('./todo/space/todo.txt','w',encoding="utf-8") as file2:
                                        file2.seek(0)
                                        todo = str(todo).replace("'", '"')
                                        file2.write(str(todo))
                                        
                    elif match.group(1) == "删除":
                        if "," in match.group(2) or "，" in match.group(2):
                            ids=match.group(2).replace("，",",")
                            ids=ids.split(",")
                            for id in ids:
                                with open('./todo/space/todo.txt','r',encoding="utf-8") as file1:
                                    todo=json.loads(file1.read().strip())

                                    if str(id) in todo:
                                        content+=f"\n[✅]已删除待办事项：id{id}:{todo[str(id)]["content"]}"
                                        del todo[str(id)]
                                    else:
                                        content+=f"\n[❌]没有找到待办事项：id{id}"
                                    with open('./todo/space/todo.txt','w',encoding="utf-8") as file2:
                                        file2.seek(0)
                                        todo = str(todo).replace("'", '"')
                                        file2.write(str(todo))
                        else:
                            with open('./todo/space/todo.txt','r',encoding="utf-8") as file1:
                                todo=json.loads(file1.read().strip())
                                if str(match.group(2)) in todo:
                                    content=f"\n[✅]已删除待办事项：id{match.group(2)}:{todo[str(match.group(2))]["content"]}"
                                    del todo[str(match.group(2))]
                                else:
                                    content=f"\n[❌]没有找到待办事项：id{match.group(2)}"
                                with open('./todo/space/todo.txt','w',encoding="utf-8") as file2:
                                    file2.seek(0)
                                    todo = str(todo).replace("'", '"')
                                    file2.write(str(todo))

                elif (match := re.match(r"[\s/]*待办(?:[\s]+(添加|完成|删除|全部)(?:[\s]+(.+))?)?", message.content)) and message.group_openid == "26EB43931720954A79D89989C3B29278":
                    if match.group(1) == None:
                        todo_total=0
                        with open('./todo/soul/todo.txt','r+',encoding="utf-8") as file1, open('./todo/soul/bird_todo.txt','r+',encoding="utf-8") as file2, open('./todo/soul/fisherman_todo.txt','r+',encoding="utf-8") as file3:
                            todo=json.loads(file1.read().strip())
                            bird_todo=json.loads(file2.read().strip())
                            fisherman_todo=json.loads(file3.read().strip())
                            for id,project in todo.items():
                                if id != "total" and message.author.member_openid == "5BA65C9F4D6E55B55892CE51A421A485" and bird_todo[id] != "无":
                                    todo_total+=1
                                    content+=f"\n[📄]id{id}: {project["content"]}\n[⛏️]其中你负责：{bird_todo[id]}\n"
                                elif id != "total" and message.author.member_openid == "27DA648A3E34BFA565FBC1813151AA07" and fisherman_todo[id] != "无":
                                    todo_total+=1
                                    content+=f"\n[📄]id{id}: {project["content"]}\n[⛏️]其中你负责：{fisherman_todo[id]}\n"
                        if content == "":
                            content="\n[❌]没有待办事项了"
                        else:
                            content+=f"\n[💻]总待办数：{todo_total}"
                    elif match.group(1) == "全部":
                        todo_total=0
                        with open('./todo/soul/todo.txt','r',encoding="utf-8") as file1:
                            todo=json.loads(file1.read().strip())
                            for id,project in todo.items():
                                if id != 'total':
                                    todo_total+=1
                                    content+=f"\n[📄]id{id}: {project["content"]}\n"
                        if content == "":
                            content="\n[❌]没有待办事项了"
                        else:
                            content+=f"\n[💻]总待办数：{todo_total}"
                    elif match.group(1) == "添加":
                        if match.group(2) == None:
                            content="\n[❌]添加什么"
                        else:
                            with open('./todo/soul/todo.txt','r+',encoding="utf-8") as file1, open('./todo/soul/bird_todo.txt','r+',encoding="utf-8") as file2, open('./todo/soul/fisherman_todo.txt','r+',   encoding="utf-8") as file3:
                                todo=json.loads(file1.read().strip())
                                bird_todo=json.loads(file2.read().strip())
                                fisherman_todo=json.loads(file3.read().strip())
                                if (new_content := re.match(r'^([^:：]+)[\s]*[:：](.+)$', match.group(2))):
                                    messages=[
                                        {"role":"system","content":'用户输入为一个待办任务，你需要分派任务给bird(处理地图/建筑)和fisherman(处理剧情/指令)，禁用"建模/代码"词，至少一人有任务，没有任务填无，必须输出仅一个严格裸JSON格式（双引号/无注释），禁用任何markdown符号，必须仅包含bird和fisherman两个键。示例模板：{"bird":"洞穴地图","fisherman":"副本剧情指令"}'},
                                    {"role": "user", "content": new_content.group(2)}
                                    ]
                                    response = aiclient.chat.completions.create(
                                    model="qwen-max",
                                    messages=messages
                                    )
                                    try:
                                        response_content=json.loads(response.choices[0].message.content)
                                        title=new_content.group(1)
                                        todo_content=new_content.group(2)
                                        bird_work=response_content["bird"]
                                        fisherman_work=response_content["fisherman"]
                                    except Exception as e:
                                        content=f"{response.choices[0].message.content}\n报错{e}"
                                        await message._api.post_group_message(group_openid=message.group_openid,msg_type=0,msg_id=message.id,content=str(content).replace('.','．'))
                                else:
                                    messages=[
                                        {"role":"system","content":'用户输入为一个代办任务，你需要生成待办标题并分派任务：bird处理地图/建筑（禁用"建模"），fisherman处理剧情/指令（禁用"代码"），至少一人有任务，没有任务填无，必须输出仅一个严格裸JSON格式（双引号/无注释），禁用任何markdown符号，必须仅包含title，bird和fisherman三个键。示例模板：{"title":"洞穴副本","bird":"洞穴地图","fisherman":"副本剧情指令"}'},
                                    {"role": "user", "content": match.group(2)}
                                    ]
                                    response = aiclient.chat.completions.create(
                                    model="qwen-max",
                                    messages=messages
                                    )
                                    try:
                                        response_content=json.loads(response.choices[0].message.content)
                                        title=response_content["title"]
                                        todo_content=match.group(2)
                                        bird_work=response_content["bird"]
                                        fisherman_work=response_content["fisherman"]
                                    except Exception as e:
                                        content=f"{response.choices[0].message.content}\n报错{e}"
                                        await message._api.post_group_message(group_openid=message.group_openid,msg_type=0,msg_id=message.id,content=str(content).replace('.','．'))
                                todo["total"]=int(todo["total"])+1
                                todo[str(todo["total"])]={"content":title+': '+todo_content, "status":{"bird": ("False" if bird_work != '无' else "True"),"fisherman": ("False" if fisherman_work != '无' else "True")}}
                                bird_todo[str(todo["total"])]=bird_work
                                fisherman_todo[str(todo["total"])]=fisherman_work
                                content=f"\n[✅]已添加待办事项：id{todo['total']}: {title}: {todo_content}，其中银鸟负责{bird_work}，深海渔民负责{fisherman_work}"
                                file1.seek(0)
                                todo = str(todo).replace("'", '"')
                                file1.write(str(todo))
                                file2.seek(0)
                                bird_todo = str(bird_todo).replace("'", '"')
                                file2.write(str(bird_todo))
                                file3.seek(0)
                                fisherman_todo = str(fisherman_todo).replace("'", '"')
                                file3.write(str(fisherman_todo))
                    elif match.group(1) == "完成":
                        if "," in match.group(2) or "，" in match.group(2):
                            ids=match.group(2).replace("，",",")
                            ids=ids.split(",")
                            for id in ids:
                                with open('./todo/soul/todo.txt','r',encoding="utf-8") as file1, open('./todo/soul/bird_todo.txt','r',encoding="utf-8") as file2, open('./todo/soul/fisherman_todo.txt','r',encoding="utf-8") as file3:
                                    todo=json.loads(file1.read().strip())
                                    bird_todo=json.loads(file2.read().strip())
                                    fisherman_todo=json.loads(file3.read().strip())
                                    if str(id) in todo:
                                        content+=f"\n[✅]已完成待办事项：id{id}:{todo[str(id)]["content"]}"
                                        if message.author.member_openid == "5BA65C9F4D6E55B55892CE51A421A485":
                                            todo[str(id)]["status"]["bird"] = "True"
                                            bird_todo[str(id)]="无"
                                        if message.author.member_openid == "27DA648A3E34BFA565FBC1813151AA07":
                                            todo[str(id)]["status"]["fisherman"]="True"
                                            fisherman_todo[str(id)]="无"
                                        if todo[str(id)]["status"]["bird"] == "True" and todo[str(id)]["status"]["fisherman"] == "True":
                                            del todo[str(id)]
                                            del bird_todo[str(id)]
                                            del fisherman_todo[str(id)]
                                    else:
                                        content+=f"\n[❌]没有找到待办事项：id{id}"
                                    with open('./todo/soul/todo.txt','w',encoding="utf-8") as file4, open('./todo/soul/bird_todo.txt','w',encoding="utf-8") as file5, open('./todo/soul/fisherman_todo.txt','w',encoding="utf-8") as file6:
                                        file4.seek(0)
                                        todo = str(todo).replace("'", '"')
                                        file4.write(str(todo))
                                        file5.seek(0)
                                        bird_todo = str(bird_todo).replace("'", '"')
                                        file5.write(str(bird_todo))
                                        file6.seek(0)
                                        fisherman_todo = str(fisherman_todo).replace("'", '"')
                                        file6.write(str(fisherman_todo))
                        else:
                            id=match.group(2)
                            with open('./todo/soul/todo.txt','r',encoding="utf-8") as file1, open('./todo/soul/bird_todo.txt','r',encoding="utf-8") as file2, open('./todo/soul/fisherman_todo.txt','r',encoding="utf-8") as file3:
                                    todo=json.loads(file1.read().strip())
                                    bird_todo=json.loads(file2.read().strip())
                                    fisherman_todo=json.loads(file3.read().strip())
                                    if str(id) in todo:
                                        content=f"\n[✅]已完成待办事项：id{id}:{todo[str(id)]["content"]}"
                                        if message.author.member_openid == "5BA65C9F4D6E55B55892CE51A421A485":
                                            todo[str(id)]["status"]["bird"] = "True"
                                            bird_todo[str(id)]="无"
                                        if message.author.member_openid == "27DA648A3E34BFA565FBC1813151AA07":
                                            todo[str(id)]["status"]["fisherman"]="True"
                                            fisherman_todo[str(id)]="无"
                                        if todo[str(id)]["status"]["bird"] == "True" and todo[str(id)]["status"]["fisherman"] == "True":
                                            del todo[str(id)]
                                            del bird_todo[str(id)]
                                            del fisherman_todo[str(id)]
                                    else:
                                        content=f"\n[❌]没有找到待办事项：id{id}"
                                    with open('./todo/soul/todo.txt','w',encoding="utf-8") as file4, open('./todo/soul/bird_todo.txt','w',encoding="utf-8") as file5, open('./todo/soul/fisherman_todo.txt','w',encoding="utf-8") as file6:
                                        file4.seek(0)
                                        todo = str(todo).replace("'", '"')
                                        file4.write(str(todo))
                                        file5.seek(0)
                                        bird_todo = str(bird_todo).replace("'", '"')
                                        file5.write(str(bird_todo))
                                        file6.seek(0)
                                        fisherman_todo = str(fisherman_todo).replace("'", '"')
                                        file6.write(str(fisherman_todo))
                    elif match.group(1) == "删除":
                        if "," in match.group(2) or "，" in match.group(2):
                            ids=match.group(2).replace("，",",")
                            ids=ids.split(",")
                            for id in ids:
                                with open('./todo/soul/todo.txt','r',encoding="utf-8") as file1, open('./todo/soul/bird_todo.txt','r',encoding="utf-8") as file2, open('./todo/soul/fisherman_todo.txt','r',encoding="utf-8") as file3:
                                    todo=json.loads(file1.read().strip())
                                    bird_todo=json.loads(file2.read().strip())
                                    fisherman_todo=json.loads(file3.read().strip())
                                    if str(id) in todo:
                                        content+=f"\n[✅]已删除待办事项：id{id}:{todo[str(id)]["content"]}"
                                        del todo[str(id)],bird_todo[str(id)],fisherman_todo[str(id)]
                                    else:
                                        content+=f"\n[❌]没有找到待办事项：id{id}"
                                    with open('./todo/soul/todo.txt','w',encoding="utf-8") as file4, open('./todo/soul/bird_todo.txt','w',encoding="utf-8") as file5, open('./todo/soul/fisherman_todo.txt','w',encoding="utf-8") as file6:
                                        file4.seek(0)
                                        todo = str(todo).replace("'", '"')
                                        file4.write(str(todo))
                                        file5.seek(0)
                                        bird_todo = str(bird_todo).replace("'", '"')
                                        file5.write(str(bird_todo))
                                        file6.seek(0)
                                        fisherman_todo = str(fisherman_todo).replace("'", '"')
                                        file6.write(str(fisherman_todo))
                        else:
                            with open('./todo/soul/todo.txt','r',encoding="utf-8") as file1, open('./todo/soul/bird_todo.txt','r',encoding="utf-8") as file2, open('./todo/soul/fisherman_todo.txt','r',encoding="utf-8") as file3:
                                todo=json.loads(file1.read().strip())
                                bird_todo=json.loads(file2.read().strip())
                                fisherman_todo=json.loads(file3.read().strip())
                                if str(match.group(2)) in todo:
                                    content=f"\n[✅]已删除待办事项：id{match.group(2)}:{todo[str(match.group(2))]["content"]}"
                                    del todo[str(match.group(2))],bird_todo[str(match.group(2))],fisherman_todo[str(match.group(2))]
                                else:
                                    content=f"\n[❌]没有找到待办事项：id{match.group(2)}"
                                with open('./todo/soul/todo.txt','w',encoding="utf-8") as file4, open('./todo/soul/bird_todo.txt','w',encoding="utf-8") as file5, open('./todo/soul/fisherman_todo.txt','w',encoding="utf-8") as file6:
                                    file4.seek(0)
                                    todo = str(todo).replace("'", '"')
                                    file4.write(str(todo))
                                    file5.seek(0)
                                    bird_todo = str(bird_todo).replace("'", '"')
                                    file5.write(str(bird_todo))
                                    file6.seek(0)
                                    fisherman_todo = str(fisherman_todo).replace("'", '"')
                                    file6.write(str(fisherman_todo))
                
                elif message.content == " 视频" and message.author.member_openid == "27DA648A3E34BFA565FBC1813151AA07":
                    url = f'https://api.bilibili.com/x/web-interface/view?bvid=BV1nmtuzJERb'
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
                    }
                    r = requests.get(url,headers=headers)
                    data = r.json()
                    content=f"\n[📄]标题：{data['data']['title']}\n[📄]简介：{data['data']['desc']}\n[📄]BV号：BV1nmtuzJERb\n[👨]UP主：{data['data']['owner']['name']}\n[🖥️]播放量：{data['data']['stat']['view']}\n[🖥️]点赞：{data['data']['stat']['like']}\n[🖥️]投币：{data['data']['stat']['coin']}\n[🖥️]收藏：{data['data']['stat']['favorite']}\n[🖥️]转发：{data['data']['stat']['share']}"
                    
                elif (match := re.match(r'^[\s/]*版本(?:\s+(发布|修改)(?:\s+([^\s:]+)(?::|\s+)(.*))?)?$', message.content)):
                    with open('./version.txt','r') as file1:
                        version=json.loads(file1.read().strip())
                        if message.group_openid == "26EB43931720954A79D89989C3B29278" and match.group(1) == "发布":
                            current_time=time.strftime("%Y年%m月%d日",time.localtime())
                            version[match.group(2)]={"content": match.group(3),"time": current_time}
                            content=f"\n[✅]已发布版本：{match.group(2)}\n发布时间：{current_time}\n版本内容：{match.group(3)}"
                            with open('./version.txt','w') as file2:
                                file2.seek(0)
                                version = str(version).replace("'", '"')
                                file2.write(str(version))
                        elif message.group_openid == "26EB43931720954A79D89989C3B29278" and match.group(1) == "修改":
                            version[match.group(2)]["content"]=match.group(3)
                            content=f"\n[✅]已修改版本：{match.group(2)}\n发布时间：{version[match.group(2)]['time']}\n版本内容：{version[match.group(2)]['content']}"
                            with open('./version.txt','w') as file2:
                                file2.seek(0)
                                version = str(version).replace("'", '"')
                                file2.write(str(version))
                        elif match.group(1) == None:
                            i = 0
                            for version_id, version_content in version.items():
                                if i >= 5:
                                    break
                                i += 1
                                content += f"\n[📄]版本：{version_id}\n   发布时间：{version_content['time']}\n   版本内容：{version_content['content']}\n"
                
                elif (match := re.match(r'^[\s/]?发病\b(?:$|\s+(.*))$', message.content)):
                    messages=[
                        {"role":"system","content":'模仿" 你说的对，但是《原神》是由米哈游自主研发的一款全新开放世界冒险游戏。游戏发生在一个被称作「提瓦特」的幻想世界，在这里，被神选中的人将被授予「神之眼」，导引元素之力。你将扮演一位名为「旅行者」的神秘角色在自由的旅行中邂逅性格各异、能力独特的同伴们，和他们一起击败强敌，找回失散的亲人——同时，逐步发掘「原神」的真相。"写一段关于用户所给内容的文案，要求句义基本一一对应，如果对应的比较勉强可以删除或修改，注意不是在原文基础上加上用户输入的内容，而是根据用户输入的内容的特点将原文原神的内容替换掉，生成内容中不应含有原神元素除非用户要求生成原神文案，注意根据事实生成，不能为了契合原文而编造事实，用户可能对所给内容进行括号内的注释解释词语意思，你的生成中不要用括号解释'},
                        {"role": "user", "content": match.group(1)}
                        ]
                    response = aiclient.chat.completions.create(
                    model="qwen-max-latest",
                    messages=messages,
                    temperature=1.999,
                    extra_body={
                        "enable_search": True
                    },
                    stream_options={"include_usage": True}
                    )

                    for chunk in responses:
                        if chunk.usage:
                            input_tokens=chunk.usage.prompt_tokens
                            output_tokens=chunk.usage.completion_tokens
                            cost=input_tokens/1000*0.0008+output_tokens/1000*0.002
                        else:
                            response += chunk.choices[0].delta.content
                    content = f'\n]{response}\n-内容来自{ai_using}\n-本次用量：输入{input_tokens}tokens，输出{output_tokens}tokens，价格{cost}元'
                    
                elif (match := re.match(r'^[\s/()]*mc[\s/()]+([\s\S]+)$', message.content, re.IGNORECASE)):
                    SIMILARITY_THRESHOLD = 0.4
                    TOP_K = 20
                    query_text = match.group(1).strip()
                    if query_text:
                        # 只做mc检索和回答
                        qvec = model.encode([query_text], normalize_embeddings=True).astype("float32")
                        sims, I = index_mc.search(qvec, TOP_K)
                        filtered = [
                            (float(sim), metadata_mc[idx])
                            for sim, idx in zip(sims[0], I[0])
                            if sim >= SIMILARITY_THRESHOLD
                        ]
                
                        if not filtered:
                            # 没有符合阈值的，直接回复“未找到相关内容”或类似提示
                            content = "[❌] 未找到相关Minecraft Wiki内容，请尝试其他关键词。"
                        else:
                            filtered = sorted(filtered, key=lambda x: -x[0])[:TOP_K]
                            wiki_context = "\n".join(
                                f"[{p['page_title']} - {p['section_title']}]\n{p['content']}" for _, p in filtered
                            )
                
                            system_prompt = (
                                "你是Minecraft维基助手，只能基于提供的wiki内容回答用户问题，"
                                "回答时只用中文标点，不用markdown或符号，只写纯文本。"
                                f"以下是wiki内容：{wiki_context}"
                            )
                
                            messages = [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": query_text}
                            ]
                
                            response = ""
                            responses = aiclient.chat.completions.create(
                                model="qwen-plus-latest",
                                messages=messages,
                                top_p=1.0,
                                temperature=0.5,
                                stream=True,
                                stream_options={"include_usage": True}
                            )
                            for chunk in responses:
                                if hasattr(chunk, "usage") and chunk.usage:
                                    input_tokens = chunk.usage.prompt_tokens
                                    output_tokens = chunk.usage.completion_tokens
                                elif (
                                    hasattr(chunk, "choices") and
                                    chunk.choices and
                                    hasattr(chunk.choices[0], "delta") and
                                    hasattr(chunk.choices[0].delta, "content") and
                                    chunk.choices[0].delta.content
                                ):
                                    response += chunk.choices[0].delta.content
                
                            content = f"[🗣️] {response}\n- 内容来自 MC Wiki + qwen-plus-latest\n输入token：{input_tokens}，输出token：{output_tokens}"
                    
                else:
                    ai_using = "qwen-plus-latest"
                    with open('./chated.txt','r',encoding="utf-8") as file1:
                        chated=json.loads(file1.read().strip())
                        if message.author.member_openid not in chated:
                            chated[message.author.member_openid]=1
                            content = f"\n[⭕️]你还没有使用过本机器人，使用前请先阅读使用说明，此信息仅会在你第一次@机器人且附带内容不是任何固定指令时发送\n[📄]使用说明：\n1.机器人聊天功能分为两种模式：wiki搜索模式和闲聊模式。若你发给机器人的内容会被一般文字处理ai识别为关于Rantindom项目的问题，则会自动检索wiki并基于wiki内容给予你回复。若你发给机器人的内容与Rantindom关系不大，则会进入闲聊模式\n2.机器人不论哪个模式，均不支持上下文，如果你的上文有尚未解决的问题，你可能需要将你的之前的问题和机器人的回复作为上文整体输入到你本次的问题中，或复制机器人的回复指出其中的修改意见，不支持上下文是因为token很贵，深海渔民不是很想费大量token解决这个事情。\n3.我们明确会收集你在使用wiki搜索时输入的问题和机器人的回复，以用于微调支持机器人检索wiki的模型，因此你需要注意不要将你不想透露的个人信息发至任何qq群，当然也包括发给任何机器人，即使你发送了，深海渔民会手动清洗数据，你的个人信息依然不会被用于微调模型，但深海渔民会看到你所发送的内容。如果你不想被收集对话，可以@机器人发送“强制闲聊”，发送以后你的任何问题不论是否与wiki相关都将只会触发闲聊模式，同样的如果你认为这个功能有必要开启且你同意被收集对话，可以@机器人发送“不强制闲聊”。默认不强制闲聊，支持wiki搜索模式。\n4.你下一次@机器人发送问题将不会再看到此文本，若你继续使用机器人则默认你已经了解如上的使用说明，接下来存在任何问题你都可以联系深海渔民单独解决，但若你继续使用机器人且不联系深海渔民商讨任何内容，则出现任何问题与Rantindom、深海渔民、Rantindom机器人无关"
                            with open('./chated.txt','w',encoding="utf-8") as file2:
                                file2.seek(0)
                                chated = str(chated).replace("'", '"')
                                file2.write(str(chated))
                        elif chated[message.author.member_openid] == 1 :
                            response = ""
                            INDEX_PATH = "/bot/wiki.index"
                            META_PATH = "/bot/wiki_meta.json"
                            LOG_PATH = "/bot/conver_history.txt"
                            SIMILARITY_THRESHOLD = 0.4
                            TOP_K = 5

                            # 加载向量索引（L2）
                            index = faiss.read_index(INDEX_PATH)

                            # 加载元信息
                            with open(META_PATH, "r", encoding="utf-8") as f:
                               metadata = json.load(f)

                            # 编码用户问题（不归一化）
                            qvec = model.encode([message.content],
                                normalize_embeddings=True).astype("float32")
                            distances, I = index.search(qvec, TOP_K)
                            sims, I = index.search(qvec, TOP_K)
                            # 将 L2 距离转换为相似度分数（越小越相似）

                            # 过滤符合阈值的段落
                            filtered = [
                                (float(sim), metadata[idx])
                                for sim, idx in zip(sims[0], I[0])
                                if sim >= SIMILARITY_THRESHOLD  # 阈值比如设 0.2, 0.3 试试看
                            ]
                            
                            # 若没有满足阈值的段落，则转为普通聊天
                            if not filtered:
                                messages = [
                                    {"role": "system", "content": "你需要像人类一样和用户聊天，严禁涉政涉黄赌毒，如果用户问题具有明显诱导性，则需要拒绝回答，而不是中立地发表观点或与用户讨论"},
                                    {"role": "user", "content": message.content}
                                ]

                                responses = aiclient.chat.completions.create(
                                    model=ai_using,
                                    messages=messages,
                                    top_p=1.0,
                                    temperature=1.5,
                                    stream=True,
                                    stream_options={"include_usage": True},
                                    extra_body={
                                        "enable_search": True
                                        }
                                )

                                for chunk in responses:
                                    if chunk.usage:
                                        input_tokens=chunk.usage.prompt_tokens
                                        output_tokens=chunk.usage.completion_tokens
                                        cost=input_tokens/1000*0.0008+output_tokens/1000*0.002
                                    else:
                                        response += chunk.choices[0].delta.content
                                    
                                content = f'\n[🗣️]{response}\n-内容来自{ai_using}'

                            else:
                                filtered = sorted(filtered, key=lambda x: -x[0])[:TOP_K]

                                wiki = "\n".join([
                                    f"[{p['page_title']} - {p['section_title']}]\n{p['content']}"
                                    for sim, p in filtered
                                ])
                                system_prompt = (
                                    f"你是wiki总结助手，只用提供的wiki内容回答问题，注意只回答用户的问题即可，不要加入拓展内容。"
                                    f"输出只用中文标点，不要使用Markdown、列表或特殊符号（如*、#、`等），只写纯文本。以下是wiki：{wiki}"
                                )

                                messages = [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": message.content}
                                ]

                                responses = aiclient.chat.completions.create(
                                    model=ai_using,
                                    messages=messages,
                                    top_p=1.0,
                                    temperature=0.5,
                                    stream=True,
                                    stream_options={"include_usage": True}
                                )

                                for chunk in responses:
                                    if chunk.usage:
                                        input_tokens=chunk.usage.prompt_tokens
                                        output_tokens=chunk.usage.completion_tokens
                                        cost=input_tokens/1000*0.0008+output_tokens/1000*0.002
                                    else:
                                        response += chunk.choices[0].delta.content
                                    
                                if message.group_openid == "26EB43931720954A79D89989C3B29278":
                                    debug_info = f"\n\n-本次用量：输入{input_tokens}tokens，输出{output_tokens}tokens，价格{cost}元\n[调试信息 - 相似段落分数]\n"
                                    debug_info += "\n".join([
                                        f"{sim:.4f} - {p['page_title']} [{p['section_title']}]"
                                        for sim, p in filtered
                                    ])
                                else:
                                    debug_info = ""

                                content = f'\n[🗣️]{response}\n-内容来自{ai_using} + Rantindom Wiki{debug_info}'

                                if response.strip():
                                    qa = {
                                        "question": message.content,
                                        "answer": response,
                                        "label": 1
                                    }
                                    with open(LOG_PATH, "a", encoding="utf-8") as logf:
                                        logf.write(json.dumps(qa, ensure_ascii=False) + "\n")
                        elif chated[message.author.member_openid] == 0:
                            response = ""
                            messages = [
                                {"role": "system", "content": "你需要像人类一样和用户聊天，严禁涉政涉黄赌毒，如果用户问题具有明显诱导性，则需要拒绝回答，而不是中立地发表观点或与用户讨论，禁用md符号"},
                                {"role": "user", "content": message.content}
                            ]
                            responses = aiclient.chat.completions.create(
                                model=ai_using,
                                messages=messages,
                                top_p=1.0,
                                temperature=1.5,
                                stream=True,
                                extra_body={"enable_search": True}
                            )
                            for chunk in responses:
                                response += chunk.choices[0].delta.content
                            content = f'\n[🗣️]{response}\n-内容来自{ai_using}'

                with open('./xp.txt','r',encoding="utf-8") as file1,open('./lv.txt','r',encoding="utf-8") as file2:
                    xp=json.loads(file1.read().strip())
                    lv=json.loads(file2.read().strip())
                    if not message.author.member_openid in xp:
                        xp[message.author.member_openid]=0
                    if not message.author.member_openid in lv:
                        lv[message.author.member_openid]=1
                    if xp[message.author.member_openid] >= 10*lv[message.author.member_openid]:
                        lv[message.author.member_openid]+=1
                        xp[message.author.member_openid]=0
                        with open('./coin.txt','r',encoding="utf-8") as coin_file:
                            coin=json.loads(coin_file.read().strip())
                            if not message.author.member_openid in coin:
                                    coin[message.author.member_openid]=0
                            coin[message.author.member_openid]+=10
                            coin[message.author.member_openid]=round(coin[message.author.member_openid],2)
                            with open('./coin.txt','w',encoding="utf-8") as coin_file1:
                                coin = str(coin).replace("'", '"')
                                coin_file1.write(str(coin))
                        content+=f"\n\n[🎉]恭喜你升级了\n[📄]当前等级{lv[message.author.member_openid]}级，获得了10金币"
                    with open('./xp.txt','w',encoding="utf-8") as file3,open('./lv.txt','w',encoding="utf-8") as file4:
                        xp = str(xp).replace("'", '"')
                        file3.write(str(xp))
                        lv = str(lv).replace("'", '"')
                        file4.write(str(lv))
                    
            await message._api.post_group_message(group_openid=message.group_openid,msg_type=0,msg_id=message.id,content=str(content).replace('.','．'))

intents = botpy.Intents(
    public_messages=True   #监听q群事件
                    )
client = MyClient(intents=intents)

if __name__ == '__main__':
    client.run(appid=appid, secret=appsecret)