# 街头篮球游戏 PAK 文件功能说明

> 基于 QXJL10256 源代码分析 + 现有游戏目录补充
> 分析日期：2026年3月1日

---

## 一、PAK 文件格式概述

### 1.1 格式名称
**GPACK** (Game Pack) - 游戏资源打包格式

### 1.2 文件标识
- **魔数**: `NFGP` (0x4E464750)
- **版本号**: 0x02

### 1.3 核心头文件
- 定义文件: `Source/Scud/Base/DFileGPack.h`
- 实现文件: `Source/Scud/Base/DFileGPack.cpp`

---

## 二、PAK 文件结构

### 2.1 文件头结构 (DFileGPackHeader)

| 字段 | 类型 | 说明 |
|------|------|------|
| dwIdentifier | dword | 标识符 "NFGP" |
| dwVer | dword | 版本号 |
| dwCryptMethod | dword | 加密方法 |
| dwRes1 | dword | 保留字段1 |
| dwRes2 | dword | 保留字段2 |
| dwNumShares | dword | 共享名称数量 |
| aShareName | SString* | 共享名称数组 |
| dwNumElements | dword | 元素数量 |
| aElement | DFileGPackElementHeader* | 元素头数组 |
| Suc | DFileGPackSUC | SUC结构 |

### 2.2 元素头结构 (DFileGPackElementHeader)

| 字段 | 类型 | 说明 |
|------|------|------|
| dwNameSize | dword | 文件名长度 |
| szName | char* | 文件名 |
| dwElementPos | dword | 元素在PAK中的位置 |
| dwElementSize | dword | 元素大小 |
| dwNextElement | dword | 下一个元素位置 |
| ElementBuffer | char* | 元素缓冲区 |

---

## 三、PAK 文件功能分类

### 3.1 系统核心 PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| camera.pak | 881 KB | 摄像机配置（视角、镜头参数） |
| curse.pak | 63 KB | 敏感词过滤表 |
| script.pak | 4 KB | 脚本文件 |
| simulator.pak | 312 KB | 模拟器数据 |
| text_data.pak | 1.7 MB | 文本数据（物品商店、技能商店等配置） |
| sound.pak | 554 KB | 音效配置 |
| ev_environment.pak | 712 KB | 环境事件配置 |
| hs_config.pak | 176 B | HS配置 |

### 3.2 特效相关 PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| effect.pak | 172 MB | 主特效资源包 |
| effect1.pak | 213 MB | 特效资源包1 |
| effect2.pak | 70 MB | 特效资源包2 |
| effect3.pak | 17 MB | 特效资源包3 |
| effect_tutorial.pak | 36 KB | 教程特效 |

### 3.3 技能相关 PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| skill.pak | 38 MB | 主技能数据包 |
| skill2.pak ~ skill12.pak | 5~114 MB | 技能数据包（各版本技能） |
| skill_icon.pak | 8.7 MB | 技能图标 |
| skilllevel_icon.pak | 1.2 MB | 技能等级图标 |

### 3.4 场景/地图 PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| stage01.pak ~ stage102.pak | 6~48 MB | 场景/地图数据（不同球场） |
| stage_myroom_1.pak | 22 MB | 我的房间场景 |
| stage_myroom_rare_gallery.pak | 1.7 MB | 我的房间稀有画廊 |
| map_text.pak | 511 B | 地图文本 |

### 3.5 篮球相关 PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| basketball_skin.pak | 4.9 MB | 篮球皮肤资源 |
| u_basketballskin.pak | 65 B | 篮球皮肤UI |
| ur_basketballskin.pak | 221 KB | 篮球皮肤UI资源 |

### 3.6 动画相关 PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| ActionSlot.pak | 66 MB | 主动作槽资源 |
| ActionSlot1.pak ~ ActionSlot7.pak | 34~59 MB | 动作槽资源包 |
| animation_list.pak | 234 KB | 动画列表 |
| macroanim.pak | 1.9 KB | 宏动画 |
| macro8.pak | 196 KB | 宏动画8 |
| motion_icon.pak | 10.5 MB | 动作图标 |

### 3.7 角色相关 PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| npc.pak | 62 MB | NPC数据 |
| face_id.pak | 16.6 MB | 脸型ID数据 |
| observer_face.pak | 2.3 MB | 观察者脸型 |
| cheerleader_icon.pak | 2.4 MB | 啦啦队图标 |
| Ceremony_PA_AIDA.pak | 23.4 MB | 典礼AIDA动画 |
| Ceremony_PA_AIDA_M.pak | 22 MB | 典礼AIDA_M动画 |
| ceremonyskin.pak | 1.1 MB | 典礼皮肤 |
| CharCollection.pak | 7.7 MB | 角色收集 |
| specialcharacter_info.pak | 1 MB | 特殊角色信息 |

### 3.8 徽章/成就相关 PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| badgepack.pak | 1.2 MB | 徽章包 |
| EmblemIcon.pak | 158 KB | 徽章图标 |
| u_emblem.pak | 65 B | 徽章UI |
| ur_emblem.pak | 19.8 MB | 徽章UI资源 |
| RecordNoteIcon.pak | 98 KB | 记录笔记图标 |
| RewardIcon.pak | 332 KB | 奖励图标 |
| teambuff_icon.pak | 154 KB | 队伍增益图标 |
| teamlogo.pak | 457 KB | 队伍标志 |

### 3.9 UI 相关 PAK（主要界面）

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| u_background.pak | 65.6 MB | 背景UI资源（登录、大厅背景等） |
| ui_background.pak | 10.7 MB | 背景UI（旧版） |
| u_login.pak | 1.3 MB | 登录界面UI |
| ui_login.pak | 1.4 MB | 登录界面UI（旧版） |
| ur_login.pak | 1.3 MB | 登录界面UI资源 |
| u_lobby.pak | 2 MB | 大厅界面UI |
| ui_lobby.pak | 605 KB | 大厅界面UI（旧版） |
| ur_lobby.pak | 172 KB | 大厅界面UI资源 |
| u_game.pak | 12.5 MB | 游戏内UI |
| ui_game.pak | 1.6 MB | 游戏内UI（旧版） |
| ur_game.pak | 3.7 MB | 游戏内UI资源 |
| u_shop.pak | 3.8 MB | 商店界面UI |
| ui_shop.pak | 1.4 MB | 商店界面UI（旧版） |
| ur_shop.pak | 1.6 MB | 商店界面UI资源 |
| u_room.pak | 1.7 MB | 房间界面UI |
| ui_room.pak | 1.6 MB | 房间界面UI（旧版） |
| ur_room.pak | 1.7 MB | 房间界面UI资源 |
| u_channel.pak | 4.8 MB | 频道界面UI |
| ui_channel.pak | 2.6 MB | 频道界面UI（旧版） |
| ur_channel.pak | 382 KB | 频道界面UI资源 |
| u_club.pak | 3.7 MB | 俱乐部界面UI |
| ui_club.pak | 618 KB | 俱乐部界面UI（旧版） |
| ur_club.pak | 49 KB | 俱乐部界面UI资源 |
| u_popup.pak | 1.1 MB | 弹窗UI |
| ui_popup.pak | 538 KB | 弹窗UI（旧版） |
| ur_popup.pak | 1.1 MB | 弹窗UI资源 |
| u_rank.pak | 427 KB | 排名界面UI |
| ui_rank.pak | 295 KB | 排名界面UI（旧版） |
| ur_rank.pak | 737 KB | 排名界面UI资源 |
| u_loading.pak | 1.6 MB | 加载界面UI |
| ui_loading.pak | 3.8 MB | 加载界面UI（旧版） |
| loading_icon.pak | 13 MB | 加载图标 |
| loadingtip.pak | 721 B | 加载提示 |

### 3.10 创建角色 UI PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| u_create_character.pak | 65 B | 创建角色UI |
| ui_createchar.pak | 1.5 MB | 创建角色UI |
| ur_create_character.pak | 3 MB | 创建角色UI资源 |
| ur_createchar_*.pak | 各异 | 各版本角色创建UI（如Neo、SuperStar、Immortals等） |

### 3.11 SAP 相关 PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| sap.pak | 49 MB | 主SAP资源 |
| sap2.pak ~ sap29.pak | 各异 | SAP资源包 |
| sap_f.pak | 35.8 MB | SAP女性角色资源 |
| sap_f2.pak ~ sap_f29.pak | 各异 | SAP女性角色资源包 |
| sap_item.pak | 19.5 MB | SAP物品资源 |
| sap_item2.pak ~ sap_item26.pak | 各异 | SAP物品资源包 |
| sap_new.pak | 23.4 MB | SAP新资源 |
| sap_new2.pak ~ sap_new6.pak | 各异 | SAP新资源包 |
| sap_npc.pak | 107 MB | SAP NPC资源 |
| sap_cheer.pak | 11.2 MB | SAP啦啦队资源 |
| sap_Skill.pak | 5.9 MB | SAP技能资源 |
| sap_sp*.pak | 各异 | SAP特殊技能资源 |
| sap_vslobby.pak | 18.8 MB | VS大厅SAP资源 |

### 3.12 活动 UI PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| ur_event_banner.pak | 59 MB | 活动横幅UI |
| ur_event_*.pak | 各异 | 各类活动UI资源（如新年、圣诞、万圣节等） |
| u_event*.pak | 各异 | 活动UI资源 |
| EventBannerData.pak | 1.3 KB | 活动横幅数据 |
| EventRewardIcon.pak | 41 KB | 活动奖励图标 |
| episode.pak | 5.3 MB | 章节/剧集资源 |

### 3.13 其他功能 PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| title.pak | 36.3 MB | 称号资源 |
| minigame.pak | 18.6 KB | 小游戏资源 |
| mission.pak | 4.5 KB | 任务资源 |
| wordpuzzle.pak | 116 KB | 文字拼图游戏 |
| crowd_info.pak | 4.2 KB | 观众信息 |
| court_ground_ad.pak | 295 KB | 球场地面广告 |
| ad.pak | 6.4 KB | 广告资源 |
| mycourt1.pak | 44 B | 我的球场 |
| myroom_ani_1.pak | 14.8 MB | 我的房间动画 |
| myroom_data.pak | 39 KB | 我的房间数据 |
| newclub.pak | 6.6 MB | 新俱乐部资源 |
| profile_icon.pak | 780 KB | 个人资料图标 |
| profile_name_effect.pak | 10.8 MB | 个人资料名称特效 |
| piece_icon.pak | 2.7 MB | 碎片图标 |
| hotgirl_mission.pak | 2.7 KB | 热辣女孩任务 |
| simulationmode_play.pak | 3.2 MB | 模拟模式游戏 |
| item_text.pak | 1.5 MB | 物品文本 |

### 3.14 游戏 UI 资源 PAK

| PAK 文件名 | 大小 | 功能说明 |
|------------|------|----------|
| u_bingo.pak / ur_bingo.pak | 637 KB / 636 KB | 宾果游戏UI |
| u_challenge.pak | 629 KB | 挑战UI |
| u_challengemode.pak | 534 KB | 挑战模式UI |
| ur_ChallengeMode.pak | 525 KB | 挑战模式UI资源 |
| u_faction.pak | 9 MB | 派系UI |
| u_fame.pak | 61 KB | 名声UI |
| u_gameofdice.pak | 44 B | 骰子游戏UI |
| u_guide_book.pak | 2.9 MB | 指导书UI |
| u_halfprice.pak | 2.3 MB | 半价UI |
| u_hotdeal.pak | 664 KB | 热门交易UI |
| u_item_collection.pak | 147 KB | 物品收集UI |
| u_league_career.pak | 1.7 MB | 联赛生涯UI |
| u_masterpass.pak | 797 KB | 大师通行证UI |
| u_mercenary.pak | 432 KB | 雇佣兵UI |
| u_mission.pak | 66 KB | 任务UI |
| u_myskill.pak | 742 KB | 我的技能UI |
| u_newrankmode.pak | 2.1 MB | 新排名模式UI |
| u_newresult.pak | 698 KB | 新结果UI |
| u_observer.pak | 586 KB | 观察者UI |
| u_oraksil.pak | 908 KB | Oraksil UI |
| u_piecesystem.pak | 810 KB | 碎片系统UI |
| u_pluscardshop.pak | 425 KB | 加值卡商店UI |
| u_privatecheerleader.pak | 159 KB | 私人啦啦队UI |
| u_replay.pak | 63 KB | 回放UI |
| u_result.pak | 832 KB | 结果UI |
| u_singleplay.pak | 845 KB | 单人游戏UI |
| u_specialskinshop.pak | 607 KB | 特殊皮肤商店UI |
| u_specialteam.pak | 297 KB | 特殊队伍UI |
| u_tournament.pak | 294 KB | 锦标赛UI |
| u_whisperofangel.pak | 12.7 MB | 天使低语UI |

### 3.15 不需要详细列出的 PAK（数量众多）

| 分类 | 文件数量 | 说明 |
|------|---------|------|
| **item*.pak** | 400+ | 物品数据包（各类服装、道具等） |
| **icon*.pak** | 400+ | 图标资源包（各类物品图标） |
| **res*.pak** | 400+ | 通用资源包（角色模型、贴图等） |

---

## 四、PAK 文件命名规则

### 4.1 前缀说明

| 前缀 | 含义 |
|------|------|
| `u_` | UI资源（新版） |
| `ui_` | UI资源（旧版） |
| `ur_` | UI资源（资源包） |
| `sap_` | SAP资源（角色动作、模型） |
| `stage` | 场景/地图 |
| `effect` | 特效 |
| `skill` | 技能 |
| `item` | 物品 |
| `icon` | 图标 |
| `res` | 资源 |

### 4.2 后缀说明

| 后缀 | 含义 |
|------|------|
| `_ext` | 扩展包 |
| `_old` | 旧版本 |
| `_effect` | 特效版本 |
| `_mission` | 任务相关 |

---

## 五、PAK 文件处理 API

### 5.1 主要类

| 类名 | 说明 |
|------|------|
| DFileGPack | PAK文件操作类 |
| DFileGPackManager | PAK文件管理器 |
| DFileGPackHeader | PAK文件头 |
| DFileGPackElementHeader | PAK元素头 |

### 5.2 主要方法

| 方法名 | 功能说明 |
|--------|----------|
| LoadPack() | 加载PAK文件 |
| UnloadPack() | 卸载PAK文件 |
| SeekFile() | 在PAK中查找文件 |
| FindFile() | 检查文件是否存在 |
| SearchFileWithWildCard() | 通配符搜索 |
| Open() | 打开PAK中的文件 |
| Close() | 关闭文件 |
| GetSize() | 获取文件大小 |
| GetFile() | 获取文件指针 |

### 5.3 文件查找算法

使用**二分查找**在PAK中定位文件：
1. 元素按文件名排序
2. 转换为小写后比较
3. 时间复杂度 O(log n)

---

## 六、扩展包机制

### 6.1 扩展包命名规则
- 原始包: `xxx.pak`
- 扩展包: `xxx_ext.pak`

### 6.2 加载优先级
1. 优先加载扩展包 (`*_ext.pak`)
2. 如果扩展包不存在，加载原始包

### 6.3 用途
- 增量更新
- 补丁分发
- 资源替换

---

## 七、相关源代码文件

| 文件路径 | 说明 |
|----------|------|
| `Scud\Base\DFileGPack.h` | PAK文件格式定义 |
| `Scud\Base\DFileGPack.cpp` | PAK文件读写实现 |
| `GameEx\GameApp.cpp` | 游戏初始化PAK加载 |
| `GameEx\TextManager.h` | 文本管理器头文件 |
| `GameEx\TextManager.cpp` | 文本PAK加载实现 |
| `GameEx\TableResource.h` | 表格资源头文件 |
| `GameEx\TableResource.cpp` | 表格PAK加载实现 |
| `GameEx\CurseFilter.cpp` | 敏感词过滤PAK加载 |

---

## 八、注意事项

1. **文件名大小写**: PAK内部文件名不区分大小写（查找时转为小写）
2. **文件名排序**: 元素必须按文件名排序才能正确查找
3. **扩展包优先**: 存在扩展包时优先使用扩展包
4. **内存管理**: PAK文件在游戏运行期间保持打开状态
5. **加密支持**: 预留了加密方法字段，但未在源代码中实现

---

**文档版本**: 1.1
**最后更新**: 2026年3月1日
**数据来源**: QXJL10256 源代码 + 现有游戏目录
