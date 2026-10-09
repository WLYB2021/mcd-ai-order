---
name: 麦麦AI点单助手
description: 在 WorkBuddy 对话里直接浏览麦当劳菜单、选餐加购、实时计算券后价并一键下单的 AI2UI 点单 Skill。当用户说"帮我点麦当劳""看看今天有啥吃的""我想点个麦辣鸡腿堡""帮我下单/结账"时使用。
---

# 麦麦AI点单助手 (McdAIPoint)

把麦当劳点餐做成"**对话即界面（AI2UI）**"：用户不用打开 App，在 WorkBuddy 里一句话就能看菜单、选餐、算最便宜的价格、确认后下单并拿到支付链接。

## 核心定位：AI2UI

传统做法是 Agent 输出一段文字推荐。本 Skill 用 **AI 直接生成 UI**：

- 用**卡片式菜单**（分类 / 名称 / 价格 / 标签 / 热量）呈现 `query-meals` 的结果
- 用**"购物车 + 实时报价"**呈现 `calculate-price` 的结果
- 用户通过自然语言（"加一个麦辣鸡腿堡""饮料换成可乐""不要薯条"）完成操作，Agent 负责把意图翻译成麦当劳 MCP 工具调用

## 前置条件

- 已在 WorkBuddy 配置并启用 `mcd-mcp` 连接器（配置见 `mcp-config.example.json`）
- 用户已登录自己的麦当劳账号（MCP Token 对应该账号，**下单会真实进入该账号**）

## 执行流程（严格按顺序）

1. **确认场景**：询问用户「到店自取」还是「麦乐送外送」。
2. **定位门店**
   - **到店**：调用 `query-nearby-stores`（到店自取传 `beType=1`），列出附近门店让用户选择。
   - **外送**：调用 `delivery-query-addresses` 取已有配送地址；若无地址，用 `delivery-create-address` 新建；再用 `delivery-query-stores` 取可配送门店。
3. **展示菜单（AI2UI）**：调用 `query-meals`（带 `storeId` + `orderType`）拿到菜单，用卡片 UI 分分类展示（名称、价格、标签、热量）。可用 `list-nutrition-foods` 补充热量标签。
4. **选餐加购**：用户用自然语言点餐，Agent 解析为餐品 `code` 列表。套餐可用 `query-meal-detail` 展示组成 / 可替换项。
5. **算价（含券）**：调用 `query-store-coupons`（到店）或 `query-my-coupons` + `available-coupons`（外送）找可用券，调用 `calculate-price` 计算商品金额、优惠、配送费、应付总价，用"购物车"UI 展示明细。
6. **⚠️ 确认下单（强制守卫）**：把最终订单（门店、商品、优惠、应付金额）完整念给用户，**必须等用户明确说"确认 / 下单 / 结账"后才调用 `create-order`**。绝不在未确认时下单，绝不猜测用户意图自动下单。
7. **下单**：`create-order` 返回订单详情与支付链接，转给用户。可提示用 `query-order` 查进度、`cancel-order` 取消。

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
