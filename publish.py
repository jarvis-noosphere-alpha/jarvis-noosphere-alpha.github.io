#!/usr/bin/env python3
"""Собирает индексируемое зеркало салон-блога на GitHub Pages.

Источник: https://salon-ai-blog.spru.site (там платформа Spru ставит
X-Robots-Tag: noindex, поэтому поисковики страницы не берут).
Зеркало живёт на github.io, где такого заголовка нет.
"""
import os
import re
import sys
import urllib.parse
import urllib.request

SRC = "https://salon-ai-blog.spru.site"
MIRROR = "https://jarvis-noosphere-alpha.github.io"
OUT = "_site"

UA = {"User-Agent": "Mozilla/5.0 (compatible; site-mirror/1.0)"}

EXTRA_ASSETS = [
    "/styles.css",
    "/img/hero.png",
    "/img/hero.svg",
    "/robots.txt",
    "/checklist-utechek-zapisi.pdf",
    "/wb-5-oshibok-kartochki.pdf",
    "/yunit-ekonomika-salona.pdf",
]


def fetch(path):
    url = SRC + path
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def mirror_url(path):
    if path.endswith("/"):
        return f"{MIRROR}{path}"
    return f"{MIRROR}/{path.strip('/')}"


YM_VERIFICATION = "3924572dfd6f1636"


def rewrite_html(text, path):
    # Форма лида должна уйти на живой эндпоинт Spru (на зеркале его нет).
    text = text.replace('action="/f/lead-blog"', f'action="{SRC}/f/lead-blog"')
    # Подтверждение прав в Яндекс.Вебмастере: код исходного домена не подходит
    # для зеркала, поэтому заменяем его на код github.io.
    text = re.sub(
        r'<meta[^>]*name=["\']yandex-verification["\'][^>]*>',
        f'<meta name="yandex-verification" content="{YM_VERIFICATION}">',
        text,
    )
    if "yandex-verification" not in text:
        text = text.replace(
            "</head>",
            f'<meta name="yandex-verification" content="{YM_VERIFICATION}">\n</head>',
            1,
        )
    # Метка верификации Pinterest относится к исходному домену — на зеркале не нужна.
    text = re.sub(r'<meta[^>]*p:domain_verify[^>]*>\s*', "", text)
    # Канонический URL и явный разрешающий robots.
    if 'rel="canonical"' not in text:
        text = text.replace(
            "</head>",
            f'<link rel="canonical" href="{mirror_url(path)}">\n'
            '<meta name="robots" content="index, follow, max-image-preview:large">\n'
            "</head>",
            1,
        )
    return text


def write_file(rel_path, data):
    full = os.path.join(OUT, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    with open(full, "wb") as f:
        f.write(data)


def write_verification_file():
    """Файл подтверждения прав в Яндекс.Вебмастере (HTML_FILE)."""
    html = (
        "<html>\n    <head>\n"
        '        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n'
        "    </head>\n"
        f"    <body>Verification: {YM_VERIFICATION}</body>\n"
        "    </body>\n"
        "</html>\n"
    )
    write_file("yandex_" + YM_VERIFICATION + ".html", html)


def main():
    os.makedirs(OUT, exist_ok=True)

    # 1) Список страниц берём из sitemap источника.
    sm = fetch("/sitemap.xml").decode("utf-8", "replace")
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    paths = []
    for loc in locs:
        if not loc.startswith(SRC):
            continue
        p = loc[len(SRC):] or "/"
        paths.append(p)

    seen = set()
    ordered = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            ordered.append(p)

    ok = 0
    for p in ordered:
        try:
            body = fetch(p)
        except Exception as e:
            print(f"SKIP {p}: {e}", file=sys.stderr)
            continue
        rel = p.strip("/")
        if rel == "":
            rel = "index.html"
        elif p.endswith("/"):
            rel = rel + "/index.html"
        if p.endswith(".pdf"):
            write_file(rel, body)
        else:
            write_file(rel, rewrite_html(body.decode("utf-8", "replace"), p))
        ok += 1
        print(f"OK {p} -> {rel}")

    for a in EXTRA_ASSETS:
        try:
            body = fetch(a)
        except Exception as e:
            print(f"SKIP asset {a}: {e}", file=sys.stderr)
            continue
        write_file(a.lstrip("/"), body)
        print(f"OK asset {a}")

    # Sitemap указывает на зеркало, а не на исходный noindex-домен.
    sm_out = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
              "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"]
    for p in ordered:
        loc = mirror_url(p if p.endswith("/") or "." in p.split("/")[-1] else p + "/")
        sm_out.append(f"  <url><loc>{loc}</loc></url>")
    sm_out.append("</urlset>")
    write_file("sitemap.xml", "\n".join(sm_out) + "\n")

    write_verification_file()
    print(f"DONE: {ok} pages, output in {OUT}/")


if __name__ == "__main__":
    main()
