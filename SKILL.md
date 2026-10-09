---
name: 麦麦AI点单助手
description: 在 WorkBuddy 对话里直接浏览麦当劳菜单、选餐加购、实时计算券后价并一键下单的 AI2UI 点单 Skill。当用户说"帮我点麦当劳""看看今天有啥吃的""我想点个巨无霸""帮我下单/结账"时使用。
---

# 麦麦AI点单助手 (McdAIPoint)

把麦当劳点餐做成"**对话即界面（AI2UI）**"：用户不用打开 App，在 WorkBuddy 里一句话就能看菜单、选餐、算最便宜的价格、确认后下单并拿到支付链接。底层全部走麦当劳官方 MCP（`mcd-mcp`）。

## 核心定位：AI2UI

传统做法是 Agent 输出一段文字推荐。本 Skill 用 **AI 直接生成 UI**：

- 用**门店卡片**呈现 `query-nearby-stores` 结果（店名 / 地址 / 距离 / 营业状态）
- 用**菜单分类卡片**呈现 `query-meals` 的结果：每个餐品用 `query-meal-detail` 拿到的 `name` + `image`（图片 URL）+ `tags` 渲染成可点卡片
- 用**"购物车 + 实时报价"**呈现 `calculate-price` 的结果（`productPrice` / `originalPrice` / `discount` / `price`）
- 用户通过自然语言（"加一个巨无霸""饮料换成可乐""不要薯条"）完成操作，Agent 负责把意图翻译成麦当劳 MCP 工具调用

> 渲染卡片优先用 WorkBuddy 的 `show_widget`（传入 `image` 图片 URL 做可视化卡片）；若不可用在对话中以结构化列表呈现，效果等价。

## 前置条件

- 已在 WorkBuddy 配置并启用 `mcd-mcp` 连接器（配置见 `mcp-config.example.json`）
- 用户已登录自己的麦当劳账号（MCP Token 对应该账号，**下单会真实进入该账号**）

## 执行流程（严格按顺序）

1. **确认场景**：询问用户「到店自取」还是「麦乐送外送」。
   - 到店：`orderType=1`，`beType=1`
   - 外送：`orderType=2`，`beType=1`（外送地址走 `delivery-query-addresses` / `delivery-create-address` / `delivery-query-stores` 分支）

2. **定位门店**
   - 调用 `query-nearby-stores`，参数：`beType=1`、`searchType=2`（关键词搜索模式）、`city`（如"北京"）、`keyword`（如"国贸"）。
   - 返回 `data[]`，每条含：`storeCode`（门店唯一编号，后续所有入参都用它）、`storeName`、`address`、`distance`、`businessStatus`、`businessStartTime` / `businessEndTime`、`reservation`（是否支持预约）、`reservationTimeOptions`。
   - 用**门店卡片**展示，让用户选择 → 记下 `storeCode`。（`beCode` 通常返回空，非必填，忽略即可。）

3. **展示菜单（AI2UI）**
   - 调用 `query-meals`，参数：`storeCode`、`orderType`、`beType`。
   - 返回 `data.categories[]`：`{ name: 分类名, meals: [{ code, tags[] }] }`。
   - ⚠️ `query-meals` **只给 `code` + `tags`，不含名称/图片/价格**。为渲染卡片，对每个要展示的餐品调用 `query-meal-detail`（`storeCode`+`orderType`+`beType`+`code`）拿 `name`、`image`（图片 URL）、`modification`（可选加料项）。
   - 用**菜单分类卡片**（图 + 名 + 标签）呈现，用户点击或自然语言点餐。

4. **选餐加购**
   - 用户自然语言点餐 → Agent 解析为 `items: [{ code, quantity }]`（注意字段是 `quantity`，不是 `count`）。
   - 套餐/单品可用 `query-meal-detail` 的 `modification.items` 展示可选加料（如巨无霸酱、吉士，通常 `price:0` 免费），用户可调整选择。

5. **算价（含券）**
   - 可选：先 `auto-bind-coupons` 一键领麦麦省券，或 `query-store-coupons`(到店) / `query-my-coupons`(卡包) 找可用券。
   - 调用 `calculate-price`，参数：`storeCode`、`orderType`、`beType`、`items:[{code, quantity}]`（可带 `takeWayCode` 取餐方式）。
   - 返回 `data`：`productOriginalPrice`、`productPrice`、`originalPrice`、`discount`、`price`（应付总价）、`productList[]`、`takeWayList[]`（取餐方式：`eat-in` 堂食 / `take-in-store` 外带）。
   - 用**购物车卡片**展示明细（单价、优惠、应付、取餐方式）。

6. **⚠️ 确认下单（强制守卫）**
   - 把最终订单（门店、商品、优惠、应付金额、取餐方式）完整念给用户，**必须等用户明确说"确认 / 下单 / 结账"后才调用 `create-order`**。
   - 绝不在未确认时下单，绝不猜测用户意图自动下单。

7. **下单**
   - `create-order` 参数：`storeCode`、`orderType`、`beType`、`items:[{code, quantity}]`、`takeWayCode`（取餐方式码，来自 `takeWayList`）、`needTableware`（是否需要餐具）、`remark`（备注）。
   - 返回订单详情与支付链接，转给用户。可提示 `query-order` 查进度、`cancel-order` 取消。

## 真实字段速查

| 工具 | 必填参数 | 关键返回 |
|---|---|---|
| query-nearby-stores | `beType`, `searchType=2`, `city`, `keyword` | `data[].storeCode` / `storeName` / `address` / `distance` / `businessStatus` |
| query-meals | `storeCode`, `orderType`, `beType` | `data.categories[].meals[].code` / `tags` |
| query-meal-detail | `storeCode`, `orderType`, `beType`, `code` | `data.name` / `image` / `modification.items` |
| calculate-price | `storeCode`, `orderType`, `beType`, `items[{code,quantity}]` | `data.price` / `productPrice` / `discount` / `productList` / `takeWayList` |
| create-order | `storeCode`, `orderType`, `beType`, `items[{code,quantity}]`, `takeWayCode` | 订单详情 + 支付链接 |

> 注：`storeCode` 为门店唯一编号（实测为整数，如 `1950564`）；餐品 `code` 为字符串（如 `"1100"` 巨无霸、`"9900005411"` 套餐）。`query-meals` 的 `meals` 仅含 `code`+`tags`，名称与图片需 `query-meal-detail` 补充，价格需 `calculate-price` 计算。

## 安全与合规

- 下单是**真实交易**，必须二次确认；误下会产生真实订单与支付。
- 不展示 / 不存储真实 Token；配置文件仅使用 `${MCD_MCP_TOKEN}` 占位符。
- 价格、供应状态以麦当劳实时返回为准，所有输出加"仅供参考"提示。
- 遵守《麦当劳 MCP 服务规则》与活动规则，不刷单、不滥用接口（限流 600 次/分钟）。

## 可选增强

- **省钱**：在算价前先用 `auto-bind-coupons` 一键领麦麦省券，再参与计算。
- **营养**：按 `list-nutrition-foods` 标注热量，支持"热量不超 X kcal"筛选推荐。
- **活动**：结合 `campaign-calendar` 在点单时提示当前可进行中的活动。

## 参考

- 麦当劳 MCP 工具清单与接入：https://github.com/M-China/mcd-mcp-server
- 集成说明：见本仓库 `MCP_INTEGRATION.md`
