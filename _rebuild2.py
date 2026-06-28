import json, glob, re, os

DIR = r"C:\Users\jichu\.claude\projects\C--Users-jichu-Downloads-hvdc-mail-app\fc67c6dd-1bc7-4a91-8dd0-4511fa4e9435\tool-results"
OUT = r"C:\Users\jichu\Downloads\hvdc_mail_app\drive_links.json"

pat_pfx  = re.compile(r"^([0-9a-f]{12})_")        # 12hexchars_rest.pdf
pat_bare = re.compile(r"^([0-9a-f]{12})\.pdf$")   # 12hexchars.pdf
m = {}  # linkkey -> {id: title}
nfiles = 0
for fp in glob.glob(os.path.join(DIR, "mcp-*search_files*.txt")):
    try:
        j = json.load(open(fp, encoding="utf-8"))
    except Exception:
        continue
    for f in j.get("files", []):
        t = f.get("title", "")
        mm = pat_pfx.match(t) or pat_bare.match(t)
        if not mm:
            continue
        k = mm.group(1)
        fid = f.get("id")
        if not fid:
            continue
        m.setdefault(k, {})
        if fid not in m[k]:
            m[k][fid] = t
            nfiles += 1

# merge manual overrides (_extra.json: linkkey -> [{id,title}]) — for files
# the unstable Drive parentId pagination skips (no orderBy in the MCP).
EXTRA = r"C:\Users\jichu\Downloads\hvdc_mail_app\_extra.json"
try:
    ex = json.load(open(EXTRA, encoding="utf-8-sig"))
    for k, items in ex.items():
        m.setdefault(k, {})
        for it in items:
            m[k][it["id"]] = it["title"]
except FileNotFoundError:
    pass

# linkkey -> sorted list of {id,title}
out = {k: [{"id": i, "title": v[i]} for i in sorted(v, key=lambda x: v[x])]
       for k, v in m.items()}
json.dump(out, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, sort_keys=True, separators=(",", ":"))
print(f"linkkeys={len(out)} files={nfiles}")
k = "fff2f051e10c"
print(f"{k}: {[x['title'] for x in out.get(k, [])] or 'MISSING'}")
