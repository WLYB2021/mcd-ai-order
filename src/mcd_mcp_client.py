#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦麦AI点单助手 · 麦当劳 MCP 参考客户端 (Reference Client)
=======================================================

这是一个可直接运行的「源代码」实现：用 Python 标准库直连麦当劳 MCP
(streamable HTTP)，复刻 SKILL.md 定义的 AI2UI 点单流程——搜店、拉菜单、算价、
下单。它既可作为 Skill 的离线调试 / 演示工具，也证明本项目具备真实可运行的源码。

特点
----
- 零外部依赖（仅标准库），Python 3.9+ 可用。
- Token 读取优先级：环境变量 MCD_MCP_TOKEN > ~/.workbuddy/mcp.json。
- create-order 默认**不执行**（真实交易），需显式 --confirm。

用法
----
  export MCD_MCP_TOKEN="你的Token"
  python src/mcd_mcp_client.py demo
  python src/mcd_mcp_client.py stores --city 北京 --keyword 国贸
  python src/mcd_mcp_client.py menu  --store 1950564 --order-type 1 --be-type 1
  python src/mcd_mcp_client.py price --store 1950564 --order-type 1 --be-type 1 --item 1100:1 --item 9900005411:1
  python src/mcd_mcp_client.py order --store 1950564 --order-type 1 --be-type 1 \
         --item 1100:1 --take-way <code> --confirm
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

MCP_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2024-11-05"


# --------------------------------------------------------------------------- #
# Token 读取
# --------------------------------------------------------------------------- #
def load_token() -> str:
    """从环境变量或 WorkBuddy mcp.json 读取 MCP Token。"""
    tok = os.environ.get("MCD_MCP_TOKEN")
    if tok:
        return tok.strip()
    candidate = os.path.expanduser("~/.workbuddy/mcp.json")
    if os.path.exists(candidate):
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            hdr = cfg["mcpServers"]["mcd-mcp"]["headers"]["Authorization"]
            return hdr.replace("Bearer ", "").strip()
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] 无法从 {candidate} 读取 Token: {exc}", file=sys.stderr)
    raise SystemExit("未找到 MCP Token：请设置环境变量 MCD_MCP_TOKEN 或配置 ~/.workbuddy/mcp.json")


# --------------------------------------------------------------------------- #
# MCP 客户端（streamable HTTP）
# --------------------------------------------------------------------------- #
class McpClient:
    def __init__(self, url: str = MCP_URL, token: str = None):
        self.url = url
        self.auth = f"Bearer {token or load_token()}"
        self.session = None
        self._initialize()

    # ---- 底层 POST ----
    def _post(self, payload: dict, session=None):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        req.add_header("Authorization", self.auth)
        if session:
            req.add_header("Mcp-Session-Id", session)
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            return dict(resp.headers), resp.read().decode("utf-8", "replace"), None
        except urllib.error.HTTPError as e:
            return dict(e.headers), e.read().decode("utf-8", "replace"), e.code

    @staticmethod
    def _find_session(headers):
        for k, v in headers.items():
            if k.lower() == "mcp-session-id":
                return v
        return None

    @staticmethod
    def _parse_body(body: str):
        body = body.strip()
        if body.startswith("{"):
            return json.loads(body)
        # SSE: 解析 data: 行
        out = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    try:
                        out.append(json.loads(chunk))
                    except json.JSONDecodeError:
                        pass
        return out[0] if out else None

    def _initialize(self):
        h, b, _ = self._post({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mcd-ai-order", "version": "1.0.0"},
            },
        })
        self.session = self._find_session(h)
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, session=self.session)

    # ---- 调用工具 ----
    def call(self, name: str, arguments: dict):
        h, b, code = self._post({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }, session=self.session)
        obj = self._parse_body(b)
        if isinstance(obj, dict) and "error" in obj:
            raise RuntimeError(f"MCP 错误: {obj['error']}")
        result = (obj or {}).get("result", {})
        # 优先取结构化内容；否则解析文本
        sc = result.get("structuredContent")
        if sc is not None:
            return sc
        content = result.get("content") or []
        for c in content:
            if c.get("type") == "text":
                try:
                    return json.loads(c["text"])
                except json.JSONDecodeError:
                    return {"text": c["text"]}
        return result


# --------------------------------------------------------------------------- #
# 业务封装
# --------------------------------------------------------------------------- #
def _as_dict(obj):
    return obj if isinstance(obj, dict) else {}


def _list_of(obj, *keys):
    """从结构化结果里尽量取出一个列表（兼容 list / {data:{...}} / {...} 多种形状）。"""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if isinstance(v, list):
                return v
        data = obj.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for k in keys:
                v = data.get(k)
                if isinstance(v, list):
                    return v
    return []


def _detail(obj):
    """从结构化结果里取出最内层的 dict（兼容 list[0] / {data:{...}} / {...}）。"""
    if isinstance(obj, dict):
        data = obj.get("data")
        return data if isinstance(data, dict) else obj
    if isinstance(obj, list):
        return obj[0] if obj else {}
    return {}


def find_stores(client: McpClient, be_type: int, city: str, keyword: str, n: int = 5):
    sc = client.call("query-nearby-stores", {
        "beType": be_type, "searchType": 2, "city": city, "keyword": keyword,
    })
    return _list_of(sc, "list", "storeList", "stores")[:n]


def get_meals(client: McpClient, store_code, order_type, be_type):
    sc = client.call("query-meals", {
        "storeCode": store_code, "orderType": order_type, "beType": be_type,
    })
    return _list_of(sc, "categories", "categoryList")


def get_meal_detail(client: McpClient, store_code, order_type, be_type, code):
    sc = client.call("query-meal-detail", {
        "storeCode": store_code, "orderType": order_type, "beType": be_type, "code": code,
    })
    return _detail(sc)


def calculate_price(client: McpClient, store_code, order_type, be_type, items, take_way_code=None):
    payload = {
        "storeCode": store_code, "orderType": order_type, "beType": be_type,
        "items": items,
    }
    if take_way_code:
        payload["takeWayCode"] = take_way_code
    return client.call("calculate-price", payload)


def create_order(client: McpClient, store_code, order_type, be_type, items, take_way_code=None,
                 address_id=None, reservation_date=None, remark="", confirm=False):
    if not confirm:
        raise SystemExit("⚠️ create-order 是真实交易，必须加 --confirm 才会执行。已中止。")
    payload = {
        "storeCode": store_code, "orderType": order_type, "beType": be_type, "items": items,
    }
    if take_way_code:
        payload["takeWayCode"] = take_way_code
    if address_id:
        payload["addressId"] = address_id
    if reservation_date:
        payload["reservationDate"] = reservation_date
    if remark:
        payload["remark"] = remark[:50]
    return client.call("create-order", payload)


# --------------------------------------------------------------------------- #
# 展示辅助
# --------------------------------------------------------------------------- #
def fen_to_yuan(fen):
    """价格单位为「分」，转为「元」。"""
    try:
        return f"¥{float(fen) / 100:.2f}"
    except (TypeError, ValueError):
        return str(fen)


def show_stores(stores):
    print("\n📍 附近门店：")
    for i, s in enumerate(stores, 1):
        d = s.get("distance")
        dist = f"{d}m" if isinstance(d, (int, float)) else (d or "—")
        resv = " ✅可预约" if s.get("reservation") else ""
        print(f"  {i}. {s.get('storeName')}（{s.get('storeCode')}） 距{dist} "
              f"{'· 营业中' if s.get('businessStatus') in (1, '1', True) else ''}{resv}")


def show_menu(client: McpClient, store_code, order_type, be_type, limit=12):
    cats = get_meals(client, store_code, order_type, be_type)
    print("\n🍔 菜单（emoji 卡片 + 图片链接）：")
    count = 0
    for cat in cats:
        cname = cat.get("categoryName") or cat.get("name") or "分类"
        print(f"\n  ▸ {cname}")
        for meal in cat.get("meals") or []:
            code = meal.get("code")
            if not code:
                continue
            detail = get_meal_detail(client, store_code, order_type, be_type, code)
            d = detail
            name = d.get("name") or meal.get("name") or code
            img = d.get("image") or ""
            tags = " ".join(f"#{t}" for t in (meal.get("tags") or []) if t)
            print(f"    • {name}  [{code}]")
            if tags:
                print(f"      {tags}")
            if img:
                print(f"      🖼 图片: {img}")
            count += 1
            if count >= limit:
                return


def parse_items(specs):
    """把 '1100:1' 解析为 {'productCode':'1100','quantity':1}。"""
    items = []
    for spec in specs:
        code, _, qty = spec.partition(":")
        items.append({"productCode": code.strip(), "quantity": int(qty or 1)})
    return items


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(description="麦麦AI点单助手 · 麦当劳 MCP 参考客户端")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("stores", help="搜索附近门店")
    ps.add_argument("--city", required=True)
    ps.add_argument("--keyword", required=True)
    ps.add_argument("--be-type", type=int, default=1)
    ps.add_argument("--n", type=int, default=5)

    pm = sub.add_parser("menu", help="拉取菜单（含图片链接）")
    pm.add_argument("--store", required=True)
    pm.add_argument("--order-type", type=int, default=1)
    pm.add_argument("--be-type", type=int, default=1)
    pm.add_argument("--limit", type=int, default=12)

    pp = sub.add_parser("price", help="计算价格")
    pp.add_argument("--store", required=True)
    pp.add_argument("--order-type", type=int, default=1)
    pp.add_argument("--be-type", type=int, default=1)
    pp.add_argument("--item", action="append", required=True, help="productCode:quantity，可多次")
    pp.add_argument("--take-way", default=None)

    po = sub.add_parser("order", help="创建订单（真实交易，需 --confirm）")
    po.add_argument("--store", required=True)
    po.add_argument("--order-type", type=int, default=1)
    po.add_argument("--be-type", type=int, default=1)
    po.add_argument("--item", action="append", required=True, help="productCode:quantity，可多次")
    po.add_argument("--take-way", default=None)
    po.add_argument("--address-id", default=None)
    po.add_argument("--reservation-date", default=None)
    po.add_argument("--remark", default="")
    po.add_argument("--confirm", action="store_true")

    pd = sub.add_parser("demo", help="只读演示：搜店→菜单→算价")

    args = p.parse_args()
    client = McpClient()

    if args.cmd == "stores":
        show_stores(find_stores(client, args.be_type, args.city, args.keyword, args.n))

    elif args.cmd == "menu":
        show_menu(client, args.store, args.order_type, args.be_type, args.limit)

    elif args.cmd == "price":
        items = parse_items(args.item)
        sc = calculate_price(client, args.store, args.order_type, args.be_type, items, args.take_way)
        d = _detail(sc)
        print("\n💰 算价结果：")
        print(json.dumps(d, ensure_ascii=False, indent=2))
        price = d.get("price")
        if price is not None:
            print(f"  → 应付: {fen_to_yuan(price)}")

    elif args.cmd == "order":
        items = parse_items(args.item)
        sc = create_order(client, args.store, args.order_type, args.be_type, items,
                          args.take_way, args.address_id, args.reservation_date, args.remark, args.confirm)
        print("\n✅ 订单已创建：")
        print(json.dumps(_detail(sc), ensure_ascii=False, indent=2))

    elif args.cmd == "demo":
        print("=== 只读演示：搜店 → 菜单 → 算价 ===")
        city, kw = "北京", "国贸"
        stores = find_stores(client, 1, city, kw, 3)
        show_stores(stores)
        if not stores:
            print("未找到门店，演示结束。")
            return
        store_code = stores[0].get("storeCode")
        show_menu(client, store_code, 1, 1, 6)
        sc = calculate_price(client, store_code, 1, 1, [{"productCode": "1100", "quantity": 1}])
        d = _detail(sc)
        price = d.get("price")
        print(f"\n💰 演示算价（巨无霸×1）：{fen_to_yuan(price) if price is not None else d}")


if __name__ == "__main__":
    main()
