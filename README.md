# nonebot-session-to-uninfo

[nonebot-plugin-session-orm](https://github.com/noneplugin/nonebot-plugin-session-orm) 到 [nonebot-plugin-uninfo](https://github.com/RF-Tar-Railt/nonebot-plugin-uninfo) 的数据库迁移脚本

### 使用方式

如果你的项目的数据库用到了 `nonebot-plugin-session-orm`，并且希望迁移到 `nonebot-plugin-uninfo`，本脚本可以帮助迁移

本脚本提供了 `check_tables` `get_id_map` 方法，可以在迁移脚本中调用。

`check_tables` 用于检查 `session-orm` 和 `uninfo` 插件的表是否均已创建，
并创建 `nonebot_session_to_uninfo_id_map` 表，用于记录 `session-orm` 和 `uninfo` 插件 的 `session_persist_id` 的对应关系。

`get_id_map` 用于获取 `session_persist_id` 的对应关系字典，传入 `session-orm` 插件的 `session_persist_id` 列表，
返回 `session-orm` 到 `uninfo` 的 `session_persist_id` 对应关系字典。

具体使用方式可以参考 [0be9a1f9a444_fill_uninfo_id.py](https://github.com/noneplugin/nonebot-plugin-memes/blob/main/nonebot_plugin_memes/migrations/0be9a1f9a444_fill_uninfo_id.py)
