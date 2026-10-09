# MCP 集成说明（MCP_INTEGRATION.md）

本项目为「麦麦AI点单助手」，基于 **麦当劳中国 MCP Server（`mcd-mcp`）** 实现"对话即界面"的 AI2UI 点单能力。所有数据均来自麦当劳官方 MCP 实时接口，未做任何本地硬编码餐品/价格。

## 一、使用的麦当劳 MCP 工具

| 工具名 | 在流程中的角色 | 调用时机 |
| --- | --- | --- |
| `query-nearby-stores` | 到店场景：查询用户可点餐门店（到店自取 / 车道取餐） | 步骤 2（到店） |
| `delivery-query-addresses` | 外送场景：查询用户已有配送地址 | 步骤 2（外送） |
| `delivery-create-address` | 外送场景：新建配送地址 | 步骤 2（外送，无地址时） |
| `delivery-query-stores` | 外送场景：按地址查询可配送门店 | 步骤 2（外送） |
| `query-meals` | 查询当前门店可售餐品菜单（分类 / 餐品编码 / 标签） | 步骤 3（展示菜单） |
| `list-nutrition-foods` | 查询餐品营养成分（能量 / 蛋白 / 脂肪 / 碳水 / 钠 / 钙） | 步骤 3（热量标签，可选） |
| `query-meal-detail` | 查询餐品 / 套餐详情与组成、可替换项 | 步骤 4（套餐解析） |
| `query-store-coupons` | 到店场景：查询指定门店可用优惠券 | 步骤 5（算价含券） |
| `query-my-coupons` | 查询用户卡包已有券 | 步骤 5（算价含券，外送） |
| `available-coupons` | 查询可领取的麦麦省券 | 步骤 5（算价含券，外送） |
| `calculate-price` | 按商品列表（可含券）计算金额、优惠、配送费、应付总价 | 步骤 5（购物车报价） |
| `create-order` | 创建订单（到店 / 外送），返回订单详情与支付链接 | 步骤 7（确认后下单） |
| `query-order` | 查询订单状态 / 进度 | 下单后查进度（可选） |
| `cancel-order` | 取消订单 | 用户要求取消时（可选） |

> 说明：本项目**真实调用**上述工具，未做模拟。下单链路（`query-meals` → `calculate-price` → `create-order`）为当前参赛作品中少有的"端到端真实下单"实现。

## 二、调用流程

```
用户："帮我点麦当劳"
   │
   ├─ 确认场景：到店自取 / 麦乐送外送
   │
   ├─ 定位门店
   │     到店：query-nearby-stores ──► 用户选门店(storeId)
   │     外送：delivery-query-addresses
   │            └─(无地址) delivery-create-address
   │           delivery-query-stores ──► 用户选门店(storeId)
   │
   ├─ 展示菜单（AI2UI 卡片）
   │     query-meals(storeId, orderType) ──► 卡片 UI
   │     [可选] list-nutrition-foods ──► 热量标签
   │
   ├─ 选餐加购（自然语言 → code 列表）
   │     [套餐] query-meal-detail ──► 组成 / 可替换项
   │
   ├─ 算价（含券）
   │     query-store-coupons / query-my-coupons + available-coupons
   │     calculate-price(items, coupons) ──► 购物车报价 UI
   │
   ├─ ⚠️ 二次确认（强制）
   │     用户明确"确认/结账" ──► 才继续
   │
   └─ 下单
         create-order ──► 订单详情 + 支付链接
         [可选] query-order / cancel-order
```

## 三、业务价值

1. **降低点餐摩擦**：把"打开 App → 选门店 → 翻菜单 → 凑券 → 下单"的多步操作，压缩成一句对话，适合通勤、加班、团餐等碎片场景。
2. **AI2UI 体验创新**：菜单与购物车以可视化卡片呈现，比纯文字推荐更直观、更接近原生 App 体验，是本届参赛中少见的"界面生成"型 Skill。
3. **真实可用**：直接打通麦当劳官方点单接口，下单后即生成真实订单与支付链接，而非停留在"建议"层面。
4. **可扩展**：优惠券自动领取、热量筛选、活动联动等增强能力已预留接入点，可平滑扩展为"省心 + 省钱 + 健康"一体化助手。
