import wikipedia, re, os, json
from collections import defaultdict
import pymorphy2
from levenshtein import levenshtein

wikipedia.set_lang("ru")
m = pymorphy2.MorphAnalyzer()

def crawl(topic, n=100, out_dir="docs", url_file="doc_urls.json"):
    os.makedirs(out_dir, exist_ok=True)
    titles = wikipedia.search(topic, results=n*3)
    saved = 0
    doc_urls = {}
    for t in titles:
        if saved >= n:
            break
        try:
            page = wikipedia.page(t)
            txt = page.content
            if len(txt.strip()) < 200:
                continue
            saved += 1
            open(f"{out_dir}/{saved}.txt", "w", encoding="utf-8").write(txt)
            doc_urls[saved] = page.url
        except Exception:
            continue

    with open(url_file, "w", encoding="utf-8") as f:
        json.dump(doc_urls, f, ensure_ascii=False, indent=2)

    return saved

tok = re.compile(r"[а-яёА-ЯЁ]+", re.I)

def lemma_tokens(text):
    return [m.parse(w)[0].normal_form for w in tok.findall(text.lower())]

def build_index(docs_dir="docs", n=100):
    inv = defaultdict(set)
    vocab = set()
    for i in range(1, n+1):
        p = f"{docs_dir}/{i}.txt"
        words = lemma_tokens(open(p, encoding="utf-8").read())
        for w in set(words):
            inv[w].add(i)
            vocab.add(w)
    return inv, sorted(vocab)

def correct_and_search(query, inv, vocab, doc_urls, max_candidates=5):
    qlem = lemma_tokens(query)
    if not qlem:
        return "Пустой запрос"
    q = qlem[0]
    if q in inv:
        links = [doc_urls[i] for i in sorted(inv[q])]
        return {"query": q, "found": links, "correction": None}

    dists = [(w, levenshtein(q, w)) for w in vocab]
    dists.sort(key=lambda x: x[1])
    best = dists[:max_candidates]

    candidate_links = []
    for w, d in best:
        docs = sorted(inv[w]) if w in inv else []
        links = [doc_urls[i] for i in docs]
        candidate_links.append((w, d, links))
    return {"query": q, "found": None, "candidates": candidate_links}

if __name__ == "__main__":
    # cnt = crawl("космос", 100, "docs", "doc_urls.json")
    # print("saved:", cnt)

    inv, vocab = build_index("docs", 100)

    if os.path.exists("doc_urls.json"):
        with open("doc_urls.json", "r", encoding="utf-8") as f:
            doc_urls = json.load(f)
            doc_urls = {int(k): v for k, v in doc_urls.items()}
    else:
        doc_urls = {}

    for q in ["звезда","млечныйпуть", "плонета"]:
        res = correct_and_search(q, inv, vocab, doc_urls, max_candidates=5)
        print("\nЗапрос:", q)
        print("Нормальная форма:", res["query"])
        if res.get("found"):
            print("Точное совпадение — ссылки:")
            for link in res["found"]:
                print(" ", link)
        else:
            print("Точных совпадений нет. Кандидаты (слово, расстояние, ссылки):")
            for w, d, links in res["candidates"]:
                print(f"  {w} (dist={d}) → {links}")
