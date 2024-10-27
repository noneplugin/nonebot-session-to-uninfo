from enum import IntEnum

import sqlalchemy as sa
from alembic import op
from nonebot.log import logger
from sqlalchemy import inspect
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from strenum import StrEnum


def check_tables() -> bool:
    conn = op.get_bind()
    insp = inspect(conn)
    table_names = insp.get_table_names()
    if "nonebot_plugin_session_orm_sessionmodel" not in table_names:
        logger.warning(
            "表 nonebot_plugin_session_orm_sessionmodel 不存在，可能无需迁移"
        )
        return False
    if "nonebot_plugin_uninfo_sessionmodel" not in table_names:
        logger.warning(
            "表 nonebot_plugin_uninfo_sessionmodel 不存在，"
            "请先安装 nonebot-plugin-uninfo 插件并初始化数据库后再迁移"
        )
        return False
    if "nonebot_session_to_uninfo_id_map" not in table_names:
        op.create_table(
            "nonebot_session_to_uninfo_id_map",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("uninfo_id", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint(
                "id", name=op.f("pk_nonebot_session_to_uninfo_id_map")
            ),
            sa.UniqueConstraint("session_id", "uninfo_id", name="unique_map"),
            info={"bind_key": "nonebot_session_to_uninfo"},
        )
        logger.info("创建 nonebot_session_to_uninfo_id_map 表")
    return True


class _SupportedPlatform(StrEnum):
    console = "console"
    discord = "discord"
    dodo = "dodo"
    feishu = "feishu"
    kaiheila = "kaiheila"
    qq = "qq"
    qqguild = "qqguild"
    telegram = "telegram"
    unknown = "unknown"


class _SupportScope(StrEnum):
    """支持的平台范围"""

    qq_client = "QQClient"
    """QQ 协议端"""
    qq_guild = "QQGuild"
    """QQ 用户频道，非官方接口"""
    qq_api = "QQAPI"
    """QQ 官方接口"""
    telegram = "Telegram"
    discord = "Discord"
    feishu = "Feishu"
    dodo = "DoDo"
    kook = "Kaiheila"
    minecraft = "Minecraft"
    github = "GitHub"
    console = "Console"
    ding = "Ding"
    wechat = "WeChat"
    """微信平台"""
    wechat_oap = "WeChatOfficialAccountPlatform"
    """微信公众号平台"""
    wecom = "WeCom"
    """企业微信平台"""
    tail_chat = "TailChat"
    """Tailchat平台"""

    onebot12_other = "Onebot12"
    """ob12 的其他平台"""
    satori_other = "Satori"
    """satori 的其他平台"""

    unknown = "Unknown"
    """未知平台"""


def _platform_to_scope(platform: str, id1: str) -> str:
    if platform == _SupportedPlatform.console:
        return _SupportScope.console
    elif platform == _SupportedPlatform.discord:
        return _SupportScope.discord
    elif platform == _SupportedPlatform.dodo:
        return _SupportScope.dodo
    elif platform == _SupportedPlatform.feishu:
        return _SupportScope.feishu
    elif platform == _SupportedPlatform.kaiheila:
        return _SupportScope.kook
    elif platform == _SupportedPlatform.qq:
        if len(id1) > 12:
            return _SupportScope.qq_api
        return _SupportScope.qq_client
    elif platform == _SupportedPlatform.qqguild:
        return _SupportScope.qq_guild
    elif platform == _SupportedPlatform.telegram:
        return _SupportScope.telegram
    else:
        return _SupportScope.unknown


class _SessionLevel(IntEnum):
    LEVEL0 = 0
    LEVEL1 = 1
    LEVEL2 = 2
    LEVEL3 = 3
    NONE = 0
    PRIVATE = 1
    GROUP = 2
    CHANNEL = 3


class _SceneType(IntEnum):
    PRIVATE = 0
    """私聊场景"""
    GROUP = 1
    """群聊场景"""
    GUILD = 2
    """频道场景"""
    CHANNEL_TEXT = 3
    """子频道文本场景"""
    CHANNEL_CATEGORY = 4
    """频道分类场景"""
    CHANNEL_VOICE = 5
    """子频道语音场景"""


def _level_to_scene(
    level: int, id1: str, id2: str, id3: str
) -> tuple[int, str, int, str]:
    scene_type = -1
    scene_id = ""
    parent_scene_type = -1
    parent_scene_id = ""

    if level == _SessionLevel.PRIVATE:
        scene_type = _SceneType.PRIVATE
        scene_id = id1
    elif level == _SessionLevel.GROUP:
        scene_type = _SceneType.GROUP
        scene_id = id2
    elif level == _SessionLevel.CHANNEL:
        if not id2:
            scene_type = _SceneType.GUILD
            scene_id = id3
        else:
            scene_type = _SceneType.CHANNEL_TEXT
            scene_id = id2
            parent_scene_type = _SceneType.GUILD
            parent_scene_id = id3

    return scene_type, scene_id, parent_scene_type, parent_scene_id


def get_id_map(session_ids: list[int]) -> dict[int, int]:
    conn = op.get_bind()
    Base = automap_base()
    Base.prepare(autoload_with=conn)
    IdMap = Base.classes.nonebot_session_to_uninfo_id_map
    SessionModel = Base.classes.nonebot_plugin_session_orm_sessionmodel
    UninfoModel = Base.classes.nonebot_plugin_uninfo_sessionmodel

    id_map_dict: dict[int, int] = {}

    with Session(conn) as db_session:
        id_map_models = db_session.scalars(sa.select(IdMap)).all()
        for id_map_model in id_map_models:
            id_map_dict[id_map_model.session_id] = id_map_model.uninfo_id

        for session_id in session_ids:
            if session_id in id_map_dict:
                continue

            session_model = db_session.scalars(
                sa.select(SessionModel).where(SessionModel.id == session_id)
            ).one()
            bot_id = session_model.bot_id
            bot_type = session_model.bot_type
            platform = session_model.platform
            level = session_model.level
            id1 = session_model.id1
            id2 = session_model.id2
            id3 = session_model.id3

            self_id = bot_id
            adapter = bot_type
            scope = _platform_to_scope(platform, id1)
            scene_type, scene_id, parent_scene_type, parent_scene_id = _level_to_scene(
                level, id1, id2, id3
            )
            scene_data = {}
            parent_scene_data = None
            user_id = id1
            user_data = {}
            member_data = None

            uninfo_model = db_session.scalars(
                sa.select(UninfoModel).where(
                    sa.and_(
                        UninfoModel.self_id == self_id,
                        UninfoModel.adapter == adapter,
                        UninfoModel.scope == scope,
                        UninfoModel.scene_id == scene_id,
                        UninfoModel.scene_type == scene_type,
                        UninfoModel.parent_scene_id == parent_scene_id,
                        UninfoModel.parent_scene_type == parent_scene_type,
                        UninfoModel.user_id == user_id,
                    )
                )
            ).one_or_none()
            if uninfo_model:
                uninfo_id = uninfo_model.id
            else:
                uninfo_model = UninfoModel(
                    self_id=self_id,
                    adapter=adapter,
                    scope=scope,
                    scene_id=scene_id,
                    scene_type=scene_type,
                    scene_data=scene_data,
                    parent_scene_id=parent_scene_id,
                    parent_scene_type=parent_scene_type,
                    parent_scene_data=parent_scene_data,
                    user_id=user_id,
                    user_data=user_data,
                    member_data=member_data,
                )
                db_session.add(uninfo_model)
                db_session.commit()
                db_session.refresh(uninfo_model)
                uninfo_id = uninfo_model.id

            id_map_dict[session_id] = uninfo_id
            db_session.add(IdMap(session_id=session_id, uninfo_id=uninfo_id))
            db_session.commit()

    id_map_dict = {k: v for k, v in id_map_dict.items() if k in session_ids}
    return id_map_dict