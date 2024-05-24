from .akiManager import *
from .async_akinator import *
from .utils import *
from datetime import datetime, timedelta
from asyncio import sleep
import hoshino
from hoshino import Service, priv
from hoshino.typing import CQEvent
from hoshino.typing import MessageSegment as Seg
import os
import aiohttp
import configparser

sv_help = '''
[开始游戏] 网络天才
[结束游戏] 结束网络天才
[回答问题] 是/不是/可能是/可能不是/不知道	
[返回上一个问题] b	
[切换群网络天才开关]
私聊使用必须添加好友
'''.strip()

sv = Service(
    name='网络天才',
    visible=True,
    enable_on_default=True,
    bundle='娱乐',
    help_=sv_help
)   

#------------读取代理配置------------#
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
config.read(config_path, encoding='utf-8')
# 读取代理配置
http_proxy = config.get("Proxy", "http", fallback="http://127.0.0.1:7890")
https_proxy = config.get("Proxy", "https", fallback="http://127.0.0.1:7890")

# 设置代理字典
proxies = {
    'http://': http_proxy,
    'https://': https_proxy,
}
#----------------------------------#


yes = ['是', '是的', '对', '有', '在','yes', 'y', '1']
no = ['不是','不','不对','否', '没有', '不在', 'no','n','2']
idk = ['我不知道','不知道','不清楚','idk','3']
probably = ['可能是','也许是', '或许是', '应该是', '大概是', '4']
probablyn = ['可能不是','也许不是','或许不是', '应该不是', '大概不是','5']
back = ['返回','上一个','b','B']

#私聊数量上限
private_lmt = 5

bot = hoshino.get_bot()
akiManager = AkiManager()
akiManager.set_private_lmt(private_lmt)
answer_words = "\n（是/不是/可能是/可能不是/不知道/返回/b）"
tasks_timeout = {}  # 保存 gid 到超时任务的映射

#群聊网络天才
@sv.on_fullmatch('网络天才')
async def start_games_group(bot, ev: CQEvent):
    if not akinator_statuses.get(ev.group_id, False):
        await bot.send(ev, '群聊网络天才功能未开启，请加bot好友私聊', at_sender=False)
        return
    uid = ev.user_id
    gid = ev.group_id
    # 通过gid检查是否有该群，有该群，且返回true说明有一个游戏正在进行
    if akiManager.get_status_by_gid(gid):
        #通过gid获得对应群正在游玩的人的uid，如果没人在玩就是空的
        current_uid = akiManager.get_uid_by_gid(gid)
        if uid == current_uid:
            await bot.send(ev, f"您已经开始游戏啦")
        else:
            await bot.send(ev, f"本群[CQ:at,qq={current_uid}]正在玩，请耐心等待~")
        return
    await akinator_start(gid, uid, bot, ev)

#群聊网络天才处理回答
@sv.on_message('group')
async def answer_question_group(bot, ev: CQEvent):
    # 如果存在任何一个gid,也就代表至少有一个群正在进行游戏,会返回true
    if akiManager.is_any_game_active() is False:
        return
    # 存在至少一个游戏,检查是不是这个群的
    if akiManager.get_status_by_gid(ev.group_id) is False:
        return
    # 是这个群的，继续
    uid = ev.user_id
    gid = ev.group_id
    # 不是游戏玩家的消息，返回
    if not(uid == akiManager.get_uid_by_gid(gid)):
        return
    # 获得该玩家的回答
    reply = ev.message.extract_plain_text()
    await reply_question(reply, gid, bot, ev)

#群聊结束网络天才
@sv.on_fullmatch('结束网络天才')
async def akinator_end_group(bot,ev: CQEvent):
    gid = ev.group_id
    # 检查是不是有这个群的游戏
    if akiManager.get_status_by_gid(gid) is False:
        await bot.send(ev, '本群没有正在进行的网络天才')
        return
    # 是不是本人发送
    uid = ev.user_id
    if not(uid == akiManager.get_uid_by_gid(gid)):
        await bot.send(ev, '不能替别人结束网络天才游戏哦～')
        return
    # 结束游戏会话
    end_session_by_gid(gid)
    await bot.send(ev,'已结束本群网络天才')

###### 私聊方法 必须好友##########

# 接收开始游戏私聊
@bot.on_message('private')
async def start_games_private(ev: CQEvent):
    sub_type = ev["sub_type"].strip()
    if sub_type != "friend":
        return
    # 获得私聊内容
    content = ev['raw_message'].strip()
    if content == "网络天才":
        # 检查私聊上限
        if akiManager.is_private_lmt_reached():
            await bot.send(ev,'网络天才私聊数量已达上限，请之后再来')
            return
        # 获得uid
        uid = ev["sender"]["user_id"]
        # 特殊组合当群号
        gid = f'private_{uid}'
        # 通过gid检查是否有该群，有该群，且返回true说明有一个游戏正在进行
        if akiManager.get_status_by_gid(gid):
            #通过gid查看是否已经开始游戏
            current_uid = akiManager.get_uid_by_gid(gid)
            await bot.send(ev, f"您已经开始游戏啦")
            return
        await akinator_start(gid, uid, bot, ev)

# 接受私聊回答
@bot.on_message('private')
async def answer_question_private(ev: CQEvent):
    sub_type = ev["sub_type"].strip()
    if sub_type != "friend":
        return
    # 必须是好友
    # 检查对方是否开始了游戏
    uid = ev["sender"]["user_id"]
    gid = f'private_{uid}'
    # 检查是不是这个群（私聊）的
    if akiManager.get_status_by_gid(gid) is False:
        return
    # 是这个私聊的，继续
    # 不是游戏玩家的消息，返回
    if not(uid == akiManager.get_uid_by_gid(gid)):
        return
    # 获得该玩家的回答
    reply = ev['raw_message'].strip()
    await reply_question(reply, gid, bot, ev)

# 私聊结束网络天才
@bot.on_message('private')
async def akinator_end_private(ev: CQEvent):
    sub_type = ev["sub_type"].strip()
    if sub_type != "friend":
        return
    # 必须是好友
    #print(json.dumps(ev, indent=4, ensure_ascii=False))
    # 获得私聊内容
    content = ev['raw_message'].strip()
    if content == "结束网络天才":
        uid = ev["sender"]["user_id"]
        gid = f'private_{uid}'
        # 检查是不是有这个私聊的游戏
        if akiManager.get_status_by_gid(gid) is False:
            await bot.send(ev, '现在没有正在进行的网络天才')
            return
        # 结束游戏会话
        end_session_by_gid(gid)
        await bot.send(ev,'已结束网络天才')
        
#开启一个网络天才会话
async def akinator_start(gid, uid, bot, ev: CQEvent):
    try:
        #先保存gid和uid信息，占个位置，避免同时多开游戏
        akiManager.create_or_update_session(gid, uid, None)
        # 为这个群组创建新的 Akinator 实例
        aki_instance = Akinator(proxies)
        # 开启一个新游戏
        await aki_instance.start_game(language='cn')
        # 获得第一个问题
    except Exception as e:
        end_session_by_gid(gid)
        await bot.send(ev,f'服务器出问题了，一会再来玩吧\n{e}')
        return
    q = aki_instance.question
    # 保存一个新的游戏-群-用户 对应关系
    akiManager.create_or_update_session(gid, uid, aki_instance)
    # 启动一个定时检查是否超时的协程
    start_session_checker(gid)
    # 发送消息
    await bot.send(ev, q + answer_words)

#####################超时计时器相关##################

def start_session_checker(gid):
    """创建并启动会话检查器任务。"""
    # 设置定时任务以检查会话是否活跃
    gid_str = str(gid)
    loop = asyncio.get_running_loop()
    tasks_timeout[gid_str] = loop.create_task(session_checker(gid_str))
    
def cancel_session_checker(gid):
    """取消特定 gid 的会话检查器任务。"""
    gid_str = str(gid)
    if gid_str in tasks_timeout:
        task = tasks_timeout[gid_str]
        if task:
            task.cancel()
        del tasks_timeout[gid_str]  # 取消任务后从字典中删除

async def session_checker(gid):
    """检查特定 gid 的会话是否活跃，并且超时后结束游戏会话。"""
    gid_str = str(gid)
    try:
        while True:
            await asyncio.sleep(30)  # 等待30秒
            if not akiManager.is_game_active(gid_str):
                # 如果会话超时，结束游戏会话
                akiManager.remove_session_by_gid(gid_str)
                # 发送消息告知用户游戏已关闭
                if 'private' in gid_str:
                    uid = int(gid_str.split('_')[-1])
                    try:
                        await bot.send_private_msg(user_id=uid, message=f'已超时，网络天才游戏已结束')
                    except Exception as e:
                        print("超时私聊消息发送失败")
                        return
                else:
                    await bot.send_group_msg(group_id=gid, message="已超时，网络天才游戏已结束")
                break
    except asyncio.CancelledError:
        # 如果任务被取消（例如：用户胜利），就退出循环
        pass

#更新最后活跃时间
def update_time_by_gid(gid):
    uid = akiManager.get_uid_by_gid(gid)
    aki = akiManager.get_akigame_by_gid(gid)
    akiManager.create_or_update_session(gid, uid, aki)

######################################################
#处理回答的通用方法
async def reply_question(reply, gid, bot, ev: CQEvent):
    # 获得该玩家对应的游戏
    aki = akiManager.get_akigame_by_gid(gid)
    try:
        if reply in yes:
            r = await aki.answer('0')
        elif reply in no:
            r = await aki.answer('1')
        elif reply in idk:
            r = await aki.answer('2')
        elif reply in probably:
            r = await aki.answer('3')
        elif reply in probablyn:
            r = await aki.answer('4')
        elif reply in back:
            r = await aki.back()
        else:
            return
        # 更新最后活跃时间
        update_time_by_gid(gid)
        q = aki.question
    except Exception as e:
        await bot.send(ev, f'处理您的回答时发生错误: {e}')
        # 关闭游戏
        end_session_by_gid(gid)
        return
    #win
    if aki.win:
        name = aki.name_proposition # 角色名字
        description = aki.description_proposition # 角色描述
        pseudo = aki.pseudo 
        photo = aki.photo # 图像
        msg = f"角色名称:{name}\n角色描述：{description}\n信息提供者:{pseudo}\n" + Seg.image(photo)
        await bot.send(ev,msg)
        # 关闭游戏
        end_session_by_gid(gid)
        return
    else:
        #没猜中继续问
        await bot.send(ev,q + answer_words)

#结束一个游戏会话
def end_session_by_gid(gid):
    # 结束超时检测
    cancel_session_checker(gid)
    # 清除游戏会话
    akiManager.remove_session_by_gid(gid)

###################### 群聊网络天才开关
# 文件路径
akinator_status_file = os.path.join(os.path.dirname(__file__), 'akinator_status.json')

# 用来存储群组的网络天才状态
akinator_statuses = {}

# 载入网络天才状态
def load_akinator_statuses():
    global akinator_statuses
    # 检查文件是否存在
    if not os.path.exists(akinator_status_file):
        # 文件不存在，则创建空的状态文件
        with open(akinator_status_file, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        akinator_statuses = {}
    else:
        # 文件存在，读取内容到akinator_statuses
        with open(akinator_status_file, 'r', encoding='utf-8') as f:
            akinator_statuses = json.load(f)

# 在程序启动时调用
load_akinator_statuses()

def save_akinator_statuses():
    with open(akinator_status_file, 'w', encoding='utf-8') as f:
        json.dump(akinator_statuses, f, ensure_ascii=False, indent=4)

@sv.on_fullmatch("切换群网络天才开关")
async def switch_akinator_group(bot, ev: CQEvent):
    # 判断权限，只有用户为群管理员或为bot设置的超级管理员才能使用
    u_priv = priv.get_user_priv(ev)
    if u_priv < sv.manage_priv:
        await bot.send(ev, '抱歉，只有群管理员或超级管理员才能使用', at_sender=True)
        return
    group_id = ev.group_id
    
    # 取反群的网络天才状态
    akinator_statuses[group_id] = not akinator_statuses.get(group_id, False)

    # 保存到文件
    save_akinator_statuses()

    # 提示信息
    await bot.send(ev, '群网络天才功能已' + ('开启' if akinator_statuses[group_id] else '关闭'), at_sender=True)
    
