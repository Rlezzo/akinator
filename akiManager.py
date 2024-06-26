from datetime import datetime, timedelta

class AkiManager:
    def __init__(self):
        # 群号gid(str):uid(int)-游戏实例-刷新时间（开始时间是第一次重置）
        self.sessions = {}  # {gid: (uid, aki_instance, reset_time)}
        # private数量限制
        self.pri_count_lmt = 5
    
    def set_private_lmt(self, num):
        self.pri_count_lmt = num
        
    def count_private_sessions(self):
        """计数当前活跃的private会话数量"""
        private_sessions = [1 for gid in self.sessions if 'private' in gid]
        return sum(private_sessions)

    def is_private_lmt_reached(self):
        """检查是否达到了private会话的数量限制"""
        return self.count_private_sessions() >= self.pri_count_lmt

    def get_status_by_gid(self, gid):
        """
        检查指定群组是否有进行中的游戏。
        
        :param gid: 群ID
        :return: 布尔值，表示是否存在该群号的进行中游戏
        """
        gid_str = str(gid)
        return gid_str in self.sessions
        
    def get_uid_by_gid(self, gid):
        """
        通过群号返回用户 ID。
        
        :param gid: 群ID
        :return: 如果群号有进行中的游戏会话，则返回对应的用户 ID，否则返回 None
        """
        gid_str = str(gid)
        if gid_str in self.sessions:
            return self.sessions[gid_str]['uid']
        return None
        
    def get_akigame_by_gid(self, gid):
        gid_str = str(gid)
        # 返回对应aki实例
        if gid_str in self.sessions:
            return self.sessions[gid_str]['aki_instance']
        return None
        
    def is_any_game_active(self):
        """检查是否有任何游戏会话正在进行中。
        
        :return: 布尔值，True 表示至少有一个游戏正在进行，否则为 False。
        """
        return bool(self.sessions)
        
    def create_or_update_session(self, gid, uid, aki_instance):
        """创建或更新一个会话记录。
        
        每次用户回答问题时，这个方法都会被调用以更新会话的最后活跃时间。
        """
        self.sessions[str(gid)] = {
            'uid': int(uid),
            'aki_instance': aki_instance,
            'reset_time': datetime.now()
        }
        
    def remove_session_by_gid(self, gid):
        """移除指定群组的 Akinator 会话。"""
        gid_str = str(gid)
        if gid_str in self.sessions:
            # 从字典中移除gid键，这会删除对Akinator实例的引用
            del self.sessions[gid_str]['aki_instance']
            del self.sessions[gid_str]

    def is_game_active(self, gid, timeout_seconds=30):
        """
        检查特定 gid 的会话是否在指定的超时秒数内仍然活跃。
        
        :param gid: 群ID
        :param timeout_seconds: 会话超时时间，以秒为单位，默认30秒
        :return: 布尔值，True 表示会话活跃，False 表示会话可能已超时
        """
        gid_str = str(gid)
        # 这群没有游戏了，更不用说超时
        if gid_str not in self.sessions:
            return False
        # 获取会话的最后活跃时间
        last_active = self.sessions[gid_str]['reset_time']
        # 如果当前时间和最后活跃时间的差距超过了30s，则认为会话不活跃，返回false
        return (datetime.now() - last_active) <= timedelta(seconds=timeout_seconds)
        
