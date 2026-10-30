#!/usr/bin/env python3
"""Собираер индексируемое зеркало салон-блога на GitHub Pages.

Источник: https://salon-ai-blog.spru.site (там платформа Spru ставит
X-Robots-Tag: noindex, поэтому поисковики страницы не берут).
Зеркало живёт на github.io, где заголовка noindex нет.
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
    "/yunit-ekonomida-salona.pdf",
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


def rewrite_html(text, path):
    # Форма лида должна уйти на живой эндпоинт Spru (на зеркале его нет).
    text = text.replace('action="/f/lead-blog"', f'action="{SRC}/f/lead-blog"')
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
        write_file(a.strip("/"), body)
        print(f"OK asset {a}")

    # 2) sitemap зеркала
    urlset = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in ordered:
        if p.endswith(".pdf"):
            continue
        urlset.append(f"  <url><loc>{mirror_url(p)}</loc></url>")
    urlset.append("</urlset>")
    write_file("sitemap.xml", "\n".join(urlset) + "\n")

    # 3) robots.txt на зеркало
    robots = fetch("/robots.txt").decode("utf-8", "replace")
    robots = re.sub(r"(?im)^sitemap:.*$", "", robots).strip()
    write_file("robots.txt", robots + f"\n\nSitemap: {MIRROR}/sitemap.xml\n")

    print(f"\nDONE: {ok} pages, output in {OUT}/")


if __name__ == "__main__":
    main()
