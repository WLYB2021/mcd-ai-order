# MCP 集成说明（MCP_INTEGRATION.md）

本项目为「麦麦AI点单助手」，基于 **麦当劳中国 MCP Server（`mcd-mcp`）** 实现"对话即界面"的 AI2UI 点单能力。所有数据均来自麦当劳官方 MCP 实时接口，未做任何本地硬编码餐品/价格。下列参数均于 2026-10-09 用真实 Token 直连 `https://mcp.mcd.cn` 实测校准。

## 一、使用的麦当劳 MCP 工具

| 工具名 | 必填参数（实测） | 在流程中的角色 | 调用时机 |
| --- | --- | --- | --- |
| `query-nearby-stores` | `beType`、`searchType=2`、`city`、`keyword` | 搜附近门店，返回 `storeCode` / `reservation` / `reservationTimeOptions` | 第 1 步（选店） |
| `delivery-query-addresses` | 无 | 外送：查已有配送地址 | 第 1 步（外送） |
| `delivery-create-address` | `city`、`address`、`addressDetail`、`contactName`、`phone` | 外送：新建地址 | 第 1 步（外送，无地址时） |
| `delivery-query-stores` | `beType`、`addressId` | 外送：按地址查可配送门店 | 第 1 步（外送） |
| `campaign-calendar` | 无 | 当月活动日历（标题/优惠/领券入口） | 第 1、2 步 |
| `query-store-coupons` | `orderType`、`beType`、`storeCode` | 本店可用券 | 第 2 步 |
| `query-my-coupons` | 无 | 卡包已有券 | 第 2 步 |
| `available-coupons` | 无 | 可领麦麦省券 | 第 2 步 |
| `auto-bind-coupons` | 无 | 一键领全部麦麦省券 | 第 2 步（用户同意后） |
| `query-meals` | `storeCode`、`orderType`、`beType` | 查菜单分类与餐品 `code`+`tags`（**不含名称/价格**） | 第 2 步 |
| `query-meal-detail` | `storeCode`、`orderType`、`beType`、`code` | 补餐品 `name` / `image`(真实 https URL) / `rounds` / `modification` | 第 2 步 |
| `calculate-price` | `storeCode`、`orderType`、`beType`、`items:[{productCode,quantity,...}]`、`takeWayCode` | 算价（**单位「分」÷100=元**）/ 取餐方式 | 第 3 步 |
| `create-order` | `storeCode`、`orderType`、`beType`、`items:[{productCode,quantity,...}]`、`takeWayCode`(到店) / `addressId`(外送) | 创建订单，**返回订单详情 + 支付链接/二维码** | 第 5 步（确认后） |
| `query-order` | `orderId` | 查订单/支付状态 | 下单后（兜底） |
| `cancel-order` | `orderId` | 取消订单 | 用户要求时（兜底） |

> 实测说明：本项目**真实调用**上述工具（已用官方 Token 验证连通性与参数结构）。下单链路 `query-nearby-stores` → `query-meals` → `query-meal-detail` → `calculate-price` → `create-order` 为当前参赛作品中少有的"端到端真实下单"实现。`query-meals` 仅返回 `code`+`tags`，名称与图片由 `query-meal-detail` 补充，价格由 `calculate-price` 计算。

## 二、调用流程

```
[第0步] AskUserQuestion 一次性收集
   用餐方式 → 映射 beType/orderType
   称呼 / 手机号 / 位置或地址 → ctx 会话上下文（不再逐个追问）

[第1步] 选店 + 活动通报
   query-nearby-stores(beType, searchType=2, city, keyword)
        └─ 门店卡(含 reservation/reservationTimeOptions 预约能力)
   campaign-calendar()  → 今日活动面板
   AskUserQuestion: 选店 + 确认方式 (+预约 reservationDate)

[第2步] 主动拉优惠+活动 + 带图菜单
   并行: query-store-coupons / query-my-coupons / available-coupons / campaign-calendar
        └─ 优惠&活动面板
   query-meals → 逐个 query-meal-detail
        └─ show_widget 菜单卡(<img src=image> 内嵌，onerror 回退)

[第3步] 算价
   calculate-price(items[{productCode,quantity,couponId?,roundList?}], takeWayCode)
        └─ 购物车卡(价格÷100=元)

[第4步] 确认
   总订单卡 → AskUserQuestion(确认/修改)

[第5步] 下单 + 对话内支付
   create-order(...) → 提取支付链接/二维码 → show_widget 渲染(可点击+扫码，无需跳App)
   query-order / cancel-order 兜底
```

## 三、关键字段纠正（避免真实调用失败）

- 商品编码字段在 `calculate-price` / `create-order` 中叫 **`productCode`**（不是 `code`）；数量用 **`quantity`**。
- 价格单位为**「分」**，展示务必 ÷100。
- `searchType=2` 为关键词搜店模式，必须同时传 `city` + `keyword`；收藏为空时 `searchType=1` 会报错。
- 到店 `beType=1` 不传 `beCode`；得来速/外送/团餐必传 `beCode`（来自对应 query-stores）。
- 到店/得来速 `orderType=1` 下单必传 `takeWayCode`（取自 `calculate-price` 的 `takeWayList[].code`）；外送 `orderType=2` 必传 `addressId`。
- `query-meal-detail.image` 是真实 https URL，直接 `<img>` 渲染即可显示。
- `query-nearby-stores` 返回 `reservation`(bool) 与 `reservationTimeOptions[]`，普通门店也支持预约。

## 四、业务价值

1. **降低点餐摩擦**：把"打开 App → 选门店 → 翻菜单 → 凑券 → 下单 → 支付"的多步操作，压缩成一句对话，适合通勤、加班、团餐等碎片场景。
2. **AI2UI 体验创新**：菜单与购物车以可视化卡片呈现（图片内嵌），比纯文字推荐更直观；且下单后**对话内直接支付**，无需跳转麦当劳 App。
3. **真实可用**：直接打通麦当劳官方点单接口，下单后即生成真实订单与支付链接/二维码，而非停留在"建议"层面。
4. **主动省钱**：进点餐即并行拉本店券+卡包券+可领券+活动，帮用户用最便宜方式下单。
5. **预约能力**：识别门店 `reservation` 字段，主动提示可预约时段。
