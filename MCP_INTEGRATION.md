# MCP 集成说明（MCP_INTEGRATION.md）

本项目为「麦麦AI点单助手」，基于 **麦当劳中国 MCP Server（`mcd-mcp`）** 实现"对话即界面"的 AI2UI 点单能力。所有数据均来自麦当劳官方 MCP 实时接口，未做任何本地硬编码餐品/价格。下列参数均经官方 Token 实测校准。

## 一、使用的麦当劳 MCP 工具

| 工具名 | 必填参数（实测） | 在流程中的角色 | 调用时机 |
| --- | --- | --- | --- |
| `query-nearby-stores` | `beType=1`、`searchType=2`、`city`、`keyword` | 到店门店搜索，返回 `storeCode` | 步骤 2（到店） |
| `delivery-query-addresses` | 无 | 外送：查已有配送地址 | 步骤 2（外送） |
| `delivery-create-address` | `city`、`address`、`addressDetail`、`contactName`、`phone` | 外送：新建地址 | 步骤 2（外送，无地址时） |
| `delivery-query-stores` | `beType`、`addressId` | 外送：按地址查可配送门店 | 步骤 2（外送） |
| `query-meals` | `storeCode`、`orderType`、`beType` | 查菜单分类与餐品 `code`+`tags`（**不含名称/价格**） | 步骤 3 |
| `query-meal-detail` | `storeCode`、`orderType`、`beType`、`code` | 补餐品 `name` / `image` / `modification` 可选加料 | 步骤 3-4 |
| `list-nutrition-foods` | 无 | 营养成分数据（能量/蛋白/脂肪/碳水/钠/钙） | 步骤 3（可选） |
| `query-store-coupons` | `orderType`、`beType`、`storeCode` | 到店门店可用券 | 步骤 5 |
| `query-my-coupons` | 无 | 卡包已有券 | 步骤 5 |
| `available-coupons` | 无 | 可领麦麦省券 | 步骤 5 |
| `auto-bind-coupons` | 无 | 一键领全部麦麦省券 | 步骤 5（可选增强） |
| `calculate-price` | `storeCode`、`orderType`、`beType`、`items:[{code,quantity}]` | 算价：原价/优惠/应付 + 取餐方式 | 步骤 5 |
| `create-order` | `storeCode`、`orderType`、`beType`、`items:[{code,quantity}]`、`takeWayCode` | 创建订单，返回详情+支付链接 | 步骤 7（确认后） |
| `query-order` | `orderId` | 查订单状态/进度 | 下单后（可选） |
| `cancel-order` | `orderId`、`cancelReasonCode` | 取消订单 | 用户要求时（可选） |

> 实测说明：本项目**真实调用**上述工具（已用官方 Token 验证连通性与参数结构）。下单链路 `query-meals` → `query-meal-detail` → `calculate-price` → `create-order` 为当前参赛作品中少有的"端到端真实下单"实现。注意 `query-meals` 仅返回 `code`+`tags`，名称与图片由 `query-meal-detail` 补充，价格由 `calculate-price` 计算。

## 二、调用流程

```
用户："帮我点麦当劳"
   │
   ├─ 确认场景：到店自取(orderType=1) / 麦乐送外送(orderType=2)
   │
   ├─ 定位门店
   │     到店：query-nearby-stores(beType=1, searchType=2, city, keyword)
   │           └─► data[].storeCode / storeName / address / distance ──► 用户选 storeCode
   │     外送：delivery-query-addresses →(无地址) delivery-create-address → delivery-query-stores
   │
   ├─ 展示菜单（AI2UI 卡片）
   │     query-meals(storeCode, orderType, beType) ──► categories[].meals[].code / tags
   │     query-meal-detail(code) ──► name / image / modification ──► 卡片 UI
   │
   ├─ 选餐加购（自然语言 → items:[{code, quantity}]）
   │     [套餐] query-meal-detail ──► modification 可选加料
   │
   ├─ 算价（含券）
   │     auto-bind-coupons / query-store-coupons / query-my-coupons
   │     calculate-price(items) ──► price / productPrice / discount / takeWayList ──► 购物车报价 UI
   │
   ├─ ⚠️ 二次确认（强制）
   │     用户明确"确认/结账" ──► 才继续
   │
   └─ 下单
         create-order(items, takeWayCode) ──► 订单详情 + 支付链接
         [可选] query-order / cancel-order
```

## 三、业务价值

1. **降低点餐摩擦**：把"打开 App → 选门店 → 翻菜单 → 凑券 → 下单"的多步操作，压缩成一句对话，适合通勤、加班、团餐等碎片场景。
2. **AI2UI 体验创新**：菜单与购物车以可视化卡片呈现，比纯文字推荐更直观、更接近原生 App 体验，是本届参赛中少见的"界面生成"型 Skill。
3. **真实可用**：直接打通麦当劳官方点单接口，下单后即生成真实订单与支付链接，而非停留在"建议"层面。
4. **可扩展**：优惠券自动领取、热量筛选、活动联动等增强能力已预留接入点，可平滑扩展为"省心 + 省钱 + 健康"一体化助手。
