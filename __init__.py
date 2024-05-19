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

bot = hoshino.get_bot()
akiManager = AkiManager()
answer_words = "\n（是/不是/可能是/可能不是/不知道/返回:b）"

@sv.on_fullmatch('网络天才')
async def akinator_start(bot, ev: CQEvent):
    uid = ev['user_id']
    gid = ev['group_id']

    # 通过gid检查是否有该群，有该群，且返回true说明有一个游戏正在进行
    if akiManager.get_status_by_gid(gid):
        #通过gid获得对应群正在游玩的人的uid，如果没人在玩就是空的
        current_uid = akiManager.get_uid_by_gid(gid)
        if uid == current_uid:
            await bot.send(ev, f"您已经开始游戏啦")
        else:
            await bot.send(ev, f"本群[CQ:at,qq={current_uid}]正在玩，请耐心等待~")
        return
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
tasks_timeout = {}  # 保存 gid 到超时任务的映射
def start_session_checker(gid):
    """创建并启动会话检查器任务。"""
    # 设置定时任务以检查会话是否活跃
    loop = asyncio.get_running_loop()
    tasks_timeout[gid] = loop.create_task(session_checker(gid))
    
def cancel_session_checker(gid):
    """取消特定 gid 的会话检查器任务。"""
    if gid in tasks_timeout:
        task = tasks_timeout[gid]
        if task:
            task.cancel()
        del tasks_timeout[gid]  # 取消任务后从字典中删除
        
# 算是协程的作用
async def session_checker(gid):
    """检查特定 gid 的会话是否活跃，并且超时后结束游戏会话。"""
    try:
        while True:
            await asyncio.sleep(30)  # 等待30秒
            #await bot.send_group_msg(group_id=gid, message="记录时间：" + str(akiManager.sessions[gid]['reset_time']))
            if not akiManager.is_game_active(gid):
                # 如果会话超时，结束游戏会话
                akiManager.remove_session_by_gid(gid)
                # 发送消息告知用户游戏已关闭
                await bot.send_group_msg(group_id=gid, message="已超时，网络天才游戏已结束")
                break
    except asyncio.CancelledError:
        # 如果任务被取消（例如：用户胜利），就退出循环
        pass
#####################超时计时器相关结束##################
#更新最后活跃时间
def update_time_by_gid(gid):
    uid = akiManager.get_uid_by_gid(gid)
    aki = akiManager.get_akigame_by_gid(gid)
    akiManager.create_or_update_session(gid, uid, aki)


        
@sv.on_message('group')
async def answer_question(bot, ev: CQEvent):
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
    if not(uid == int(akiManager.get_uid_by_gid(gid))):
        return
    # 获得该玩家的回答
    reply = ev.message.extract_plain_text()
    # 更新最后活跃时间
    update_time_by_gid(gid)
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
        q = aki.question
    except Exception as e:
        await bot.send(ev, f'处理您的回答时发生错误: {e}')
        # 关闭游戏
        end_session_by_gid(gid)
        return
    
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

@sv.on_fullmatch('结束网络天才')
async def akinator_end(bot,ev: CQEvent):
    gid = ev.group_id
    # 检查是不是有这个群的游戏
    if akiManager.get_status_by_gid(ev.group_id) is False:
        await bot.send(ev, '本群没有正在进行的网络天才')
        return
    # 是不是本人发送
    uid = ev.user_id
    if not(uid == int(akiManager.get_uid_by_gid(gid))):
        await bot.send(ev, '不能替别人结束网络天才游戏哦～')
        return
    # 结束游戏会话
    end_session_by_gid(gid)
    await bot.send(ev,'已结束本群网络天才')