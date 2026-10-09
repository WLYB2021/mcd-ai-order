---
name: 麦麦AI点单助手
description: 在 WorkBuddy 对话里直接浏览麦当劳菜单、选餐加购、实时算券后价并一键下单的 AI2UI 点单 Skill。当用户说"帮我点麦当劳""看看今天有啥吃的""我想点个巨无霸""帮我下单/结账"时使用。
---

# 麦麦AI点单助手 (McdAIPoint)

把麦当劳点餐做成"**对话即界面（AI2UI）**"：用户不用打开 App，在 WorkBuddy 里一句话就能看菜单、选餐、算最便宜的价格、确认后下单，并**在对话内直接拿到支付链接/二维码完成付款**。底层全部走麦当劳官方 MCP（`mcd-mcp`）。

> 本 Skill 针对首版体验做了 5 项关键改进：① 信息一次性收集；② 选店时同步展示活动与预约能力；③ 进点餐主动拉券+活动、菜单带图；④ 一张总单确认；⑤ 下单后对话内直接支付，无需跳转 App。

## 前置条件

- 已在 WorkBuddy 配置并启用 `mcd-mcp` 连接器（配置见 `mcp-config.example.json`）
- 用户已登录自己的麦当劳账号（MCP Token 对应该账号，**下单会真实进入该账号**）

## 关键字段速查（已真机校准 2026-10-09）

| 工具 | 必填参数 | 关键返回 / 注意 |
|---|---|---|
| query-nearby-stores | `beType`, `searchType=2`, `city`, `keyword` | `storeCode` / `storeName` / `address` / `distance` / `businessStatus` / **`reservation`(bool)** / **`reservationTimeOptions[]`** |
| query-meals | `storeCode`, `orderType`, `beType` | `categories[].meals[].code` / `tags`（**只给 code+tags，无名称/价格**） |
| query-meal-detail | `+code` | `name` / **`image`（真实 https URL，可渲染）** / `rounds` / `modification` / `supportModify` |
| calculate-price | `storeCode`, `orderType`, `beType`, `items[{productCode, quantity, ...}]`, `takeWayCode` | `price` **单位为「分」，÷100=元**；`productPrice`/`discount`/`takeWayList[].code` |
| query-store-coupons | `storeCode`, `orderType`, `beType` | `data[]`: `title` / `couponId` / `couponCode` / `products[]` / `tradeDateTime` |
| campaign-calendar | 无 | `dailyList[].events[]`: `activityTitle` / `price` / `articleDto{title,content,imgList,buttonText,appJumpUrl}` |
| create-order | `storeCode`, `orderType`, `beType`, `items[{productCode,quantity,...}]`, `takeWayCode`(到店必传), `addressId`(外送必传) | **返回订单详情 + 支付链接/二维码**；堂食外带还返回取餐柜二维码 |
| query-my-coupons | 无 | 卡包券（不校验当前门店可用性） |
| available-coupons | 无 | 可领取的麦麦省券 |
| auto-bind-coupons | 无 | 一键领取全部可领麦麦省券 |

**beType / orderType 映射**（由用户选择的用餐方式决定）：
- 到店自取 → `beType=1`, `orderType=1`
- 得来速 (DT) → `beType=5`, `orderType=1`
- 麦乐送外送 → `beType=2`, `orderType=2`
- 企业团餐 → `beType=6`, `orderType=2`

> 注意：`storeCode` 为整数型字符串（如 `"1950564"`）；餐品 `code` 也为字符串（如 `"1100"` 巨无霸、`"9900005411"` 套餐）。`calculate-price` / `create-order` 的商品列表字段名是 **`productCode`**（不是 `code`），数量用 **`quantity`**；价格单位「分」，展示务必 ÷100。

## 执行流程（严格按顺序）

### 第 0 步 · 一次性信息收集（解决"取信息太碎"）

用**一次** `AskUserQuestion`（最多 4 题）把启动所需信息收齐，避免后续反复打断：

- **Q1 用餐方式**：到店自取 / 麦乐送外送 / 得来速 / 企业团餐（选择项，映射出 `beType`+`orderType`）
- **Q2 怎么称呼您**：自由文本（用"其他"输入填姓名/昵称）→ `name`
- **Q3 手机号**：自由文本（用"其他"输入）→ `phone`（仅用于下单身份，不展示原文、不持久化）
- **Q4 位置 / 收货地址**：到店填"无"或"城市+地标"(如"北京 国贸")；外送填详细收货地址 → `city`+`keyword` 或 `address`

在问题下方用自然语言补充说明：城市用于搜店、本次信息仅会话内暂存。
解析为会话上下文 `ctx = {beType, orderType, name, phone, city, keyword/address}`，后续步骤直接复用，**不再逐个追问**。

### 第 1 步 · 选店 + 活动通报（解决"应展示各店活动/预约"）

1. 调用 `query-nearby-stores`（`beType`, `searchType=2`, `city`, `keyword`）→ 取前 3–5 家候选门店。
   - 外送场景改为：`delivery-query-addresses` / `delivery-create-address` 确定 `addressId` 与地址 → `delivery-query-stores` 拿 `beCode`。
2. 调用 `campaign-calendar`() → 取今天 / 本月活动，整理为"**今日可参与活动**"面板（标题 + 优惠 + 领券入口 `appJumpUrl`）。
3. 用 `show_widget` 渲染**门店卡片 + 活动面板**：
   - 门店卡：店名 / 地址 / 距离 / 营业中? / **预约**（`reservation=true` 时展示 `reservationTimeOptions` 的日期+时段，如"夜市 17:14–21:45"）
   - 活动卡：活动标题 / 优惠力度 / "立即领券"入口
4. `AskUserQuestion` 让用户**选门店 + 确认用餐方式**；若 `reservation=true` 且用户想预约，引导其在 `reservationTimeOptions` 中选日期+时段，记录 `reservationDate`（后续传给 `query-meals`/`calculate-price`/`create-order`）。
5. 记下 `storeCode`（及外送的 `beCode`/`addressId`）。

### 第 2 步 · 主动拉优惠+活动 + 带图菜单（解决"应主动给券/活动"+"图片不显示"）

进点餐后**立即并行**调用（不等用户问）：

- `query-store-coupons(storeCode, orderType, beType)` → 本店可用券
- `query-my-coupons()` → 卡包已有券
- `available-coupons()` → 可领麦麦省券（如需，先问用户再 `auto-bind-coupons()` 一键领）
- `campaign-calendar()` → 当前活动（与第 1 步合并去重）

渲染"**优惠 & 活动**"面板：券（名称 / 适用商品 `products[].productName` / 有效期 `tradeDateTime`）、活动（标题 / 优惠 / 领券）。

随后拉菜单并**带图**渲染：

1. `query-meals(storeCode, orderType, beType)` → `categories[].meals[].code`。
2. 对每个要展示的餐品调 `query-meal-detail(storeCode, orderType, beType, code)` 拿 `name` / `image` / `rounds` / `modification` / `supportModify`。
3. 用 `show_widget` 渲染**菜单分类卡片**：`<img src="{image}">` + 名称 + 标签；`image` 为真实 https URL（`https://menu-img.mcd.cn/...`），**务必内嵌 `<img>` 标签**才能显示。
   - 加 `onerror` 回退：图片加载失败时显示 `🍔 {name}`，保证卡片永远有内容。
   - 套餐用 `rounds` 展示可选组合；`supportModify=true` 在名称后标【可特调】，特调项用 `modification`（仅用户主动问才展开）。
4. 与用户自然语言沟通确定点餐内容：支持"加一个巨无霸""饮料换可乐""不要薯条"；套餐子项经 `roundList[].comboItemList` 构造。

### 第 3 步 · 算价（含券）

调用 `calculate-price`：

- `items: [{ productCode, quantity, couponId?, couponCode?, modification?, roundList? }]`（**字段是 `productCode` 不是 `code`**；套餐带 `roundList[].comboItemList[{code, quantity, modification?}]`）
- `takeWayCode`：取 `calculate-price` 返回的 `takeWayList[].code`（到店/得来速必传）
- 如用户指定用某券，把 `couponId`/`couponCode` 带入对应 item
- **价格单位为「分」**，所有展示值 ÷100 转「元」

用 `show_widget` 渲染**购物车卡片**：单价、优惠、应付(元)、取餐方式。

### 第 4 步 · 确认下单（一张总单，问是否同意；不原则问原因）

把最终订单汇总成**一张总订单卡**（门店 / 商品×数量×单价 / 已用券 / 优惠 / 应付 / 取餐方式 / 预约(若有)），`AskUserQuestion`：

- **确认下单** → 进入第 5 步
- **修改** → 自然语言问"哪里要改"，回退到第 2/3 步调整后再确认

> ⚠️ 下单是**真实交易**，必须本步二次确认后才调用 `create-order`，绝不猜测意图自动下单。

### 第 5 步 · 下单 + 对话内支付（解决"支付太麻烦"）

1. 调用 `create-order`，参数：`storeCode`, `orderType`, `beType`, `items[{productCode, quantity, couponId?, couponCode?, modification?, roundList?}]`, `takeWayCode`(到店必传), `addressId`(外送必传), `reservationDate`(预约场景), `remark`(外送备注≤50字), `needTableware`。
2. **`create-order` 返回订单详情 + 支付链接/二维码**（官方文档确认；v1.0.9 起堂食外带还返回取餐柜二维码）。
3. 提取返回中的支付字段（`payUrl` / `paymentUrl` / `qrCode` / 取餐柜二维码等），用 `show_widget` 渲染：
   - **可点击支付链接** + **二维码图片**，提示"**在此直接支付 / 扫码即可，无需跳转麦当劳 App**"
   - 若为 `mcdapp://` 深链，提示点按用麦当劳 App 打开
4. 附：`query-order(orderId)` 查支付/配送状态、`cancel-order(orderId)` 取消。

## 渲染约定（AI2UI）

- 门店、菜单、购物车、订单、支付均优先用 `show_widget` 渲染为内联 HTML 卡片 / 面板，图片用 `<img src>` 内嵌，`onerror` 回退。
- 图片 URL 来自 `query-meal-detail.image`（真实 https，可直接渲染）。
- 若 `show_widget` 不可用，退化为结构化列表 + Markdown 图片语法 `![name](url)`，效果等价。

## 安全与合规

- 下单是**真实交易**，必须二次确认；误下会产生真实订单与支付。
- 不展示 / 不存储真实 Token；配置文件仅使用 `${MCD_MCP_TOKEN}` 占位符。
- 手机号等个人信息仅会话内用于下单，不落盘、不回显原文。
- 价格、供应状态以麦当劳实时返回为准，所有输出加"仅供参考"提示。
- 遵守《麦当劳 MCP 服务规则》与活动规则，不刷单、不滥用接口（限流 600 次/分钟）。

## 参考

- 麦当劳 MCP 工具清单与接入：https://github.com/M-China/mcd-mcp-server
- 集成说明：见本仓库 `MCP_INTEGRATION.md`
