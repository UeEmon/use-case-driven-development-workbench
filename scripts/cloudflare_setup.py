#!/usr/bin/env python3
"""Cloudflare Tunnel + Access を API で自動設定する（docs/guide/remote-access.md の B 手順）。

  make cloudflare-setup             # 対話形式で設定し、.env にトンネルのトークンを書く
  make cloudflare-setup ARGS=--delete   # 作ったものをすべて削除する

順序: Access（認証）→ トンネル → DNS。認証がかかる前に公開される瞬間を作らない。
何度実行しても同じ結果になる（既存のものは再利用・更新する）。
API トークンは画面入力または環境変数 CLOUDFLARE_API_TOKEN で渡し、どこにも保存しない。
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.cloudflare.com/client/v4"
ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
SERVICE_URL = "http://docs:8000"  # cloudflared コンテナから見た docs コンテナ

PERMISSIONS = """\
  API トークンに必要な権限（dash.cloudflare.com/profile/api-tokens → Create Token → Custom token）:
    Account | Cloudflare Tunnel | Edit
    Account | Access: Apps and Policies | Edit
    Account | Access: Organizations, Identity Providers, and Groups | Edit
    Zone    | DNS | Edit
    Zone    | Zone | Read
  Account Resources と Zone Resources は、使うアカウントとドメインに限定してください。"""


class CFError(Exception):
    pass


class Cloudflare:
    def __init__(self, token: str, dry_run: bool = False):
        self.token = token
        self.dry_run = dry_run

    def call(self, method: str, path: str, body: dict | None = None, query: dict | None = None):
        if self.dry_run and method != "GET":
            print(f"    (dry-run) {method} {path}")
            return {"id": "dry-run-id", "token": "dry-run-token"}
        url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                payload = json.load(res)
        except urllib.error.HTTPError as e:
            try:
                payload = json.load(e)
            except Exception:
                raise CFError(f"{method} {path}: HTTP {e.code}") from None
        except urllib.error.URLError as e:
            raise CFError(f"api.cloudflare.com に接続できません: {e.reason}") from None
        if not payload.get("success", False):
            msgs = "; ".join(f"[{x.get('code')}] {x.get('message')}" for x in payload.get("errors", []))
            raise CFError(f"{method} {path}: {msgs or 'unknown error'}")
        return payload.get("result")


def ask(label: str, default: str = "", env: str = "") -> str:
    if env and os.environ.get(env):
        return os.environ[env]
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def write_env(key: str, value: str) -> None:
    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8") if ENV_EXAMPLE.exists() else "", encoding="utf-8")
    text = ENV_FILE.read_text(encoding="utf-8")
    line = f"{key}={value}"
    if re.search(rf"^{key}=.*$", text, flags=re.M):
        text = re.sub(rf"^{key}=.*$", lambda _: line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    ENV_FILE.write_text(text, encoding="utf-8")


def find_zone(cf: Cloudflare, domain: str) -> tuple[str, str]:
    zones = cf.call("GET", "/zones", query={"name": domain})
    if not zones:
        raise CFError(f"ドメイン {domain} がこのアカウント（またはトークンの Zone Resources）にありません。"
                      "Cloudflare にドメインを追加済みか、トークンの権限を確認してください。")
    return zones[0]["id"], zones[0]["account"]["id"]


def ensure_zero_trust(cf: Cloudflare, account: str) -> None:
    try:
        cf.call("GET", f"/accounts/{account}/access/organizations")
    except CFError as e:
        raise CFError("Zero Trust の初期設定が済んでいないようです。dash.cloudflare.com → Zero Trust を開き、"
                      f"チーム名の設定と Free プランの選択を済ませてから再実行してください。\n  詳細: {e}") from None


def ensure_otp(cf: Cloudflare, account: str) -> str:
    idps = cf.call("GET", f"/accounts/{account}/access/identity_providers") or []
    for idp in idps:
        if idp.get("type") == "onetimepin":
            print("  ✓ ログイン方法: One-time PIN（既存）")
            return idp["id"]
    idp = cf.call("POST", f"/accounts/{account}/access/identity_providers",
                  {"name": "One-time PIN", "type": "onetimepin", "config": {}})
    print("  ✓ ログイン方法: One-time PIN を追加")
    return idp["id"]


def ensure_policy(cf: Cloudflare, account: str, name: str, emails: list[str]) -> str:
    body = {"name": name, "decision": "allow", "include": [{"email": {"email": m}} for m in emails]}
    for p in cf.call("GET", f"/accounts/{account}/access/policies") or []:
        if p.get("name") == name:
            cf.call("PUT", f"/accounts/{account}/access/policies/{p['id']}", body)
            print(f"  ✓ ポリシー更新: {', '.join(emails)} のみ許可")
            return p["id"]
    p = cf.call("POST", f"/accounts/{account}/access/policies", body)
    print(f"  ✓ ポリシー作成: {', '.join(emails)} のみ許可")
    return p["id"]


def find_app(cf: Cloudflare, account: str, hostname: str) -> dict | None:
    for app in cf.call("GET", f"/accounts/{account}/access/apps") or []:
        if app.get("domain", "").split("/")[0] == hostname:
            return app
    return None


def ensure_app(cf: Cloudflare, account: str, hostname: str, policy_id: str, idp_id: str) -> str:
    body = {
        "name": f"UCDD Workbench ({hostname})",
        "domain": hostname,
        "type": "self_hosted",
        "session_duration": "24h",
        "allowed_idps": [idp_id],
        "auto_redirect_to_identity": True,
        "policies": [{"id": policy_id, "precedence": 1}],
    }
    app = find_app(cf, account, hostname)
    if app:
        cf.call("PUT", f"/accounts/{account}/access/apps/{app['id']}", body)
        print(f"  ✓ Access アプリ更新: {hostname}")
        return app["id"]
    app = cf.call("POST", f"/accounts/{account}/access/apps", body)
    print(f"  ✓ Access アプリ作成: {hostname}")
    return app["id"]


def find_tunnel(cf: Cloudflare, account: str, name: str) -> dict | None:
    tunnels = cf.call("GET", f"/accounts/{account}/cfd_tunnel", query={"name": name, "is_deleted": "false"}) or []
    return tunnels[0] if tunnels else None


def ensure_tunnel(cf: Cloudflare, account: str, name: str) -> tuple[str, str]:
    t = find_tunnel(cf, account, name)
    if t:
        print(f"  ✓ トンネル: {name}（既存を再利用）")
        tunnel_id = t["id"]
    else:
        t = cf.call("POST", f"/accounts/{account}/cfd_tunnel", {"name": name, "config_src": "cloudflare"})
        print(f"  ✓ トンネル作成: {name}")
        tunnel_id = t["id"]
        if t.get("token"):
            return tunnel_id, t["token"]
    token = cf.call("GET", f"/accounts/{account}/cfd_tunnel/{tunnel_id}/token")
    return tunnel_id, token


def configure_ingress(cf: Cloudflare, account: str, tunnel_id: str, hostname: str) -> None:
    cf.call("PUT", f"/accounts/{account}/cfd_tunnel/{tunnel_id}/configurations", {"config": {"ingress": [
        {"hostname": hostname, "service": SERVICE_URL, "originRequest": {}},
        {"service": "http_status:404"},
    ]}})
    print(f"  ✓ ルーティング: {hostname} → {SERVICE_URL}")


def ensure_dns(cf: Cloudflare, zone: str, hostname: str, tunnel_id: str, force: bool) -> None:
    target = f"{tunnel_id}.cfargotunnel.com"
    body = {"type": "CNAME", "name": hostname, "content": target, "proxied": True,
            "comment": "UCDD Workbench (cloudflare_setup.py)"}
    records = cf.call("GET", f"/zones/{zone}/dns_records", query={"name": hostname}) or []
    for r in records:
        if r["type"] == "CNAME" and r["content"] == target:
            print(f"  ✓ DNS: {hostname}（既存）")
            return
    if records:
        desc = ", ".join(f"{r['type']} {r['content']}" for r in records)
        if not force:
            raise CFError(f"{hostname} には既に DNS レコードがあります（{desc}）。"
                          "別のサブドメインを指定するか、置き換えてよい場合は --force を付けて再実行してください。")
        for r in records:
            cf.call("DELETE", f"/zones/{zone}/dns_records/{r['id']}")
    cf.call("POST", f"/zones/{zone}/dns_records", body)
    print(f"  ✓ DNS: {hostname} → トンネル")


def setup(cf: Cloudflare, args) -> None:
    domain = ask("Cloudflare に登録済みのドメイン（例: example.com）", env="CF_DOMAIN")
    sub = ask("公開に使うサブドメイン", "ucdd", env="CF_SUBDOMAIN")
    emails_raw = ask("閲覧を許可するメールアドレス（カンマ区切り）", env="CF_ALLOW_EMAILS")
    emails = [e.strip() for e in emails_raw.split(",") if e.strip()]
    if not domain or not emails or not all(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e) for e in emails):
        raise CFError("ドメインと、正しい形式のメールアドレスを 1 つ以上入力してください。")
    hostname = f"{sub}.{domain}"
    tunnel_name = f"home-mac-{sub}"

    print(f"\n[1/5] ドメインを確認: {domain}")
    zone, account = find_zone(cf, domain)
    print(f"  ✓ アカウント {account[:8]}…, ゾーン {zone[:8]}…")
    others = [r for r in cf.call("GET", f"/zones/{zone}/dns_records", query={"name": hostname}) or []
              if not str(r.get("content", "")).endswith(".cfargotunnel.com")]
    if others and not args.force:
        desc = ", ".join(f"{r['type']} {r['content']}" for r in others)
        raise CFError(f"{hostname} は既に使われています（{desc}）。別のサブドメインを指定するか、"
                      "置き換えてよい場合は --force を付けて再実行してください。")

    print("[2/5] Access（認証）を設定 ※公開より先に設定します")
    ensure_zero_trust(cf, account)
    idp = ensure_otp(cf, account)
    policy = ensure_policy(cf, account, f"UCDD allow ({hostname})", emails)
    ensure_app(cf, account, hostname, policy, idp)

    print("[3/5] トンネルを用意")
    tunnel_id, token = ensure_tunnel(cf, account, tunnel_name)
    configure_ingress(cf, account, tunnel_id, hostname)

    print("[4/5] DNS を設定")
    ensure_dns(cf, zone, hostname, tunnel_id, args.force)

    print("[5/5] .env にトンネルのトークンを保存")
    if cf.dry_run:
        print("    (dry-run) .env は変更しません")
    else:
        write_env("CLOUDFLARE_TUNNEL_TOKEN", token)
        write_env("CLOUDFLARE_HOSTNAME", hostname)
        print(f"  ✓ {ENV_FILE.name} を更新（Git の管理対象外）")

    print(f"""
完了しました。続けて次を実行してください:

  make tunnel

数十秒後に https://{hostname} を開き、許可したメールアドレスに届くコードでログインします。
""")


def teardown(cf: Cloudflare, args) -> None:
    domain = ask("削除するドメイン（例: example.com）", env="CF_DOMAIN")
    sub = ask("サブドメイン", "ucdd", env="CF_SUBDOMAIN")
    hostname, tunnel_name = f"{sub}.{domain}", f"home-mac-{sub}"
    if not args.yes and input(f"{hostname} のトンネル・DNS・Access 設定を削除します。よろしいですか？ [y/N]: ").lower() != "y":
        print("中止しました。")
        return
    zone, account = find_zone(cf, domain)
    t = find_tunnel(cf, account, tunnel_name)
    target = f"{t['id']}.cfargotunnel.com" if t else None
    for r in cf.call("GET", f"/zones/{zone}/dns_records", query={"name": hostname}) or []:
        if r["type"] == "CNAME" and r["content"] == target:
            cf.call("DELETE", f"/zones/{zone}/dns_records/{r['id']}")
            print(f"  ✓ DNS 削除: {hostname}")
    if t:
        try:
            cf.call("DELETE", f"/accounts/{account}/cfd_tunnel/{t['id']}")
            print(f"  ✓ トンネル削除: {tunnel_name}")
        except CFError as e:
            print(f"  ! トンネルを削除できません（先に make down で cloudflared を止めてください）: {e}")
    app = find_app(cf, account, hostname)
    if app:
        cf.call("DELETE", f"/accounts/{account}/access/apps/{app['id']}")
        print(f"  ✓ Access アプリ削除: {hostname}")
    for p in cf.call("GET", f"/accounts/{account}/access/policies") or []:
        if p.get("name") == f"UCDD allow ({hostname})":
            cf.call("DELETE", f"/accounts/{account}/access/policies/{p['id']}")
            print("  ✓ ポリシー削除")
    if ENV_FILE.exists() and not cf.dry_run:
        write_env("CLOUDFLARE_TUNNEL_TOKEN", "")
        print(f"  ✓ {ENV_FILE.name} のトークンを消去")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--delete", action="store_true", help="作成したトンネル・DNS・Access 設定を削除する")
    parser.add_argument("--dry-run", action="store_true", help="確認だけ行い、Cloudflare 側は変更しない")
    parser.add_argument("--force", action="store_true", help="同名の既存 DNS レコードを置き換える")
    parser.add_argument("--yes", action="store_true", help="削除時の確認を省略する")
    args = parser.parse_args()

    print("Cloudflare Tunnel + Access 自動設定\n")
    token = os.environ.get("CLOUDFLARE_API_TOKEN") or getpass.getpass("Cloudflare API トークン（入力は表示されません）: ").strip()
    if not token:
        print(PERMISSIONS)
        return 1
    cf = Cloudflare(token, dry_run=args.dry_run)
    try:
        (teardown if args.delete else setup)(cf, args)
    except CFError as e:
        print(f"\nエラー: {e}")
        if "[10000]" in str(e) or "[9109]" in str(e) or "Authentication" in str(e):
            print(PERMISSIONS)
        return 1
    except KeyboardInterrupt:
        print("\n中止しました。")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
