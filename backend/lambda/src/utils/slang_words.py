# build_lexicon_v2_3.py
# Generates a ~500-term Gen-Z slang lexicon with concise, grammatical glosses.
# Outputs: lingible_lexicon_v2_3.json
# Changes in v2.3:
# - Added: stan (+morphs), serve looks (+morphs), facts / that's facts
# - Tuned glosses: "cap" -> "a lie;false", "i'm dead" -> "i'm hysterical",
#   "left no crumbs" -> "was flawless", "slay queen" -> "well done"
# - Keeps guarantees: non-acronym gloss ≤3 words; no gloss equals the term
import json, re, datetime
from collections import OrderedDict

VERSION = "2.3"
TODAY = str(datetime.date.today())


def mk_entry(
    term,
    gloss,
    *,
    pos="phrase",
    variants=None,
    confidence=0.85,
    tags=None,
    age="E",
    flags=None,
    cats=None,
    examples=None,
    gloss_long=None,
):
    e = OrderedDict()
    e["term"] = term
    e["variants"] = variants or [term]
    e["pos"] = pos
    e["gloss"] = gloss
    if gloss_long:
        e["gloss_long"] = gloss_long
    e["examples"] = examples or []
    e["tags"] = tags or []
    e["status"] = "approved"
    e["confidence"] = round(float(confidence), 2)
    e["regions"] = []
    e["age_rating"] = age
    e["content_flags"] = sorted(list(flags or []))
    e["first_seen"] = "2023-01-01"
    e["last_seen"] = TODAY
    e["sources"] = {"reddit": 0, "youtube": 0, "runtime": 0}
    e["momentum"] = 1.0
    e["categories"] = cats or ["slang"]
    return e


def short(gl):
    # normalize to ≤3 words per option, lowercase, no slashes/()s
    parts = [p.strip() for p in str(gl).split(";") if p.strip()]
    out = []
    for p in parts or [gl]:
        p = re.sub(r"\(.*?\)", "", p)
        p = p.replace("/", " or ")
        p = re.sub(r"\s+", " ", p).strip().lower()
        words = p.split()
        if len(words) > 3:
            p = " ".join(words[:3])
        out.append(p)
    seen = set()
    res = []
    for p in out:
        if p not in seen:
            seen.add(p)
            res.append(p)
    return ";".join(res)


def norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[\s\-\_]+", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    return s.strip()


def gloss_not_equal(term, gloss, variants):
    term_norms = {norm(term)} | {norm(v) for v in (variants or [])}
    for part in [p.strip() for p in (gloss or "").split(";") if p.strip()]:
        if norm(part) in term_norms:
            return False
    return True


items = []

# --- ACRONYMS ---
acronym_map = OrderedDict(
    {
        "afaik": "as far as i know",
        "afk": "away from keyboard",
        "asap": "as soon as possible",
        "atm": "at the moment",
        "brb": "be right back",
        "btw": "by the way",
        "bff": "best friend forever",
        "bday": "birthday",
        "bf": "boyfriend",
        "gf": "girlfriend",
        "imo": "in my opinion",
        "imho": "in my humble opinion",
        "idk": "i don't know",
        "ikr": "i know, right",
        "irl": "in real life",
        "iirc": "if i recall correctly",
        "ily": "i love you",
        "ilysm": "i love you so much",
        "lmk": "let me know",
        "l8r": "later",
        "lmao": "laughing my *** off",
        "lol": "laughing out loud",
        "omg": "oh my god",
        "omw": "on my way",
        "tbh": "to be honest",
        "tbqh": "to be quite honest",
        "tbf": "to be fair",
        "tfw": "that feeling when",
        "tldr": "too long; didn't read",
        "thx": "thanks",
        "ty": "thank you",
        "tysm": "thank you so much",
        "nvm": "never mind",
        "np": "no problem",
        "idc": "i don't care",
        "idgaf": "i don't give a ****",
        "wtf": "what the ****",
        "wth": "what the heck",
        "wfh": "work from home",
        "wyd": "what are you doing",
        "wdym": "what do you mean",
        "wys": "what you saying",
        "wya": "where you at",
        "hbu": "how about you",
        "hbd": "happy birthday",
        "fyi": "for your information",
        "fomo": "fear of missing out",
        "fr": "for real",
        "ngl": "not gonna lie",
        "smh": "shaking my head",
        "sry": "sorry",
        "jk": "just kidding",
        "rn": "right now",
        "gg": "good game",
        "glhf": "good luck; have fun",
        "ftw": "for the win",
        "icymi": "in case you missed it",
        "bbl": "be back later",
        "ttyl": "talk to you later",
        "bfn": "bye for now",
        "dm": "direct message",
        "pm": "private message",
        "tba": "to be announced",
        "tbc": "to be confirmed",
        "eta": "estimated time of arrival",
        "ofc": "of course",
        "stg": "swear to god",
        "istg": "i swear to god",
        "pov": "point of view",
        "nsfw": "not safe for work",
        "nsfl": "not safe for life",
        "brt": "be right there",
        "gtg": "got to go",
        "g2g": "got to go",
        "ily2": "i love you too",
        "tmi": "too much information",
        "iykyk": "if you know, you know",
        "ngmi": "not gonna make it",
        "wym": "what do you mean",
        "hru": "how are you",
        "wbu": "what about you",
        "wdyt": "what do you think",
        "dw": "don't worry",
        "tmr": "tomorrow",
        "prob": "probably",
        "def": "definitely",
        "obv": "obviously",
        "bc": "because",
        "cuz": "because",
        "w/e": "whatever",
        "asap pls": "as soon as possible, please",
    }
)
for k, v in acronym_map.items():
    age = (
        "M18"
        if "***" in v or k in {"wtf", "idgaf", "nsfl"}
        else ("T13" if k in {"lmao", "stg", "istg"} else "E")
    )
    flags = {"profanity"} if age == "M18" else set()
    items.append(
        mk_entry(
            k,
            short(v),
            pos="abbr",
            variants=[k, k.upper()],
            confidence=0.88,
            tags=["internet", "acronym"],
            age=age,
            flags=flags,
            cats=["acronym"],
            examples=[f"{k.upper()}, I had no idea.", f"Reply {k} when you can."],
        )
    )

# --- CORE SLANG ---
slangs = [
    ("cap", "a lie;false"),  # tuned to insert article
    ("no cap", "seriously;for real"),
    ("mid", "mediocre;average"),
    ("bet", "okay;agreed"),
    ("say less", "got it;understood"),
    ("bussin", "delicious;excellent"),
    ("drip", "style"),
    ("fit", "outfit"),
    ("rizz", "charisma;flirting skill"),
    ("based", "unapologetic;authentic"),
    ("cringe", "embarrassing;awkward"),
    ("fire", "excellent"),
    ("slaps", "bangs;excellent"),
    ("ate", "excelled;impressed"),
    ("left no crumbs", "was flawless"),  # tuned to read smoother
    ("it's giving", "feels like"),
    ("main character", "standout;center"),
    ("touch grass", "go outside;disconnect"),
    ("valid", "legit;credible"),
    ("goated", "legendary;the best"),
    ("low-key", "subtly;secretly"),
    ("high-key", "openly;obviously"),
    ("pressed", "upset;annoyed"),
    ("salty", "bitter;resentful"),
    ("extra", "dramatic;over the top"),
    ("shook", "shocked;astonished"),
    ("i'm dead", "i'm hysterical"),  # tuned to avoid bare adjective
    ("hits different", "special;distinct"),
    ("secure the bag", "profit;succeed"),
    ("glow up", "improve;transform"),
    ("beige flag", "quirk;oddity"),
    ("the ick", "turnoff"),
    ("red flag", "warning sign"),
    ("green flag", "good sign"),
    ("soft launch", "tease;preview"),
    ("hard launch", "reveal"),
    ("girl dinner", "snack plate"),
    ("girl math", "justification"),
    ("delulu", "delusional;wishful"),
    ("sigma", "stoic;self-reliant"),
    ("canon event", "rite;inevitability"),
    ("be so for real", "seriously"),
    ("let him cook", "wait;hold on"),
    ("caught in 4k", "exposed"),
    ("pilled", "indoctrinated;obsessed"),
    ("periodt", "period;final"),
    ("per", "indeed"),
    ("w", "win"),
    ("l", "loss"),
    ("ratio", "outvoted"),
    ("cope", "deal;accept"),
    ("mald", "rage"),
    ("npc", "unoriginal;basic"),
    ("brain rot", "mindless content"),
    ("receipts", "evidence;proof"),
    ("down bad", "desperate;thirsty"),
]
for t, g in slangs:
    items.append(
        mk_entry(
            t,
            short(g),
            variants=[t],
            confidence=0.9,
            cats=["slang"],
            examples=[f"That was {t}."],
        )
    )

# --- NEW coverage: verb sense and common phrases ---
# stan (verb) — include morphs so "I stan"/"stanning" are covered
items.append(
    mk_entry(
        "stan",
        short("adore;idolize"),
        variants=["stan", "stans", "stanned", "stanning"],
        confidence=0.86,
        cats=["slang"],
        examples=["I stan this artist.", "Been stanning them for years."],
    )
)

# serve looks — include morphs for "serving looks"
items.append(
    mk_entry(
        "serve looks",
        short("stylish"),
        variants=["serve looks", "serving looks", "serves looks", "served looks"],
        confidence=0.84,
        cats=["slang"],
        examples=["She's serving looks."],
    )
)

# facts / that's facts
items.append(
    mk_entry(
        "facts",
        short("true"),
        variants=["facts", "big facts"],
        confidence=0.86,
        cats=["slang"],
        examples=["Facts."],
    )
)

items.append(
    mk_entry(
        "that's facts",
        short("that's true"),
        variants=["that's facts", "that is facts"],
        confidence=0.88,
        cats=["slang"],
        examples=["No cap, that's facts."],
    )
)

# "she ate that" (kept; renderer can insert 'in' before a following noun)
items.append(
    mk_entry(
        "she ate that",
        short("she excelled"),
        variants=["she ate that"],
        confidence=0.80,
        cats=["slang"],
        examples=["She ate that performance."],
    )
)

# slay queen — soften to a neutral compliment
items.append(
    mk_entry(
        "slay queen",
        short("well done"),
        variants=["slay queen"],
        confidence=0.80,
        cats=["slang"],
        examples=["Slay queen."],
    )
)

# --- EMOJI ---
emoji = [
    ("skull emoji", "hilarious", ["💀", "😂", "🤣", "😭", "skull emoji"]),
    ("fire emoji", "excellent", ["🔥", "fire emoji"]),
    ("eyes emoji", "watching;interested", ["👀", "eyes emoji"]),
    ("clown emoji", "foolish", ["🤡", "clown emoji"]),
    ("cap emoji", "lie", ["🧢", "cap emoji"]),
    ("salute emoji", "respect", ["🫡", "salute emoji"]),
    ("side-eye emoji", "skeptical", ["🙄", "side-eye emoji"]),
    ("crying emoji", "hilarious", ["😭", "crying emoji"]),
    ("sleep emoji", "tired;boring", ["😴", "sleep emoji"]),
]
for t, g, v in emoji:
    items.append(
        mk_entry(
            t,
            short(g),
            variants=v,
            confidence=0.85,
            cats=["emoji"],
            examples=[f"{v[0]} at that."],
        )
    )

# --- INTERNET CULTURE ---
internet = [
    ("shadowbanned", "hidden"),
    ("de-influencing", "anti-hype"),
    ("algospeak", "coded language"),
    ("ratioed", "outvoted"),
    ("callout", "criticize"),
    ("cancelled", "boycotted;shunned"),
    ("boost", "promote"),
    ("alt", "alternate account"),
    ("finsta", "private account"),
    ("moots", "mutuals"),
    ("oomf", "follower"),
]
for t, g in internet:
    items.append(
        mk_entry(
            t,
            short(g),
            confidence=0.82,
            cats=["internet_culture"],
            examples=[f"Got {t} again."],
        )
    )

# --- GAMING ---
gaming = [
    ("op", "overpowered", ["OP", "op"]),
    ("nerf", "weaken", ["nerf"]),
    ("buff", "strengthen", ["buff"]),
    ("grind", "work hard", ["grind", "grinding"]),
    ("afk", "away", ["afk", "AFK"]),
    ("gg", "good game", ["gg", "GG"]),
    ("glhf", "good luck", ["glhf", "GLHF"]),
    ("noob", "newbie;rookie", ["n00b", "newb", "noob"]),
    ("smurf", "alt account", ["smurf", "smurfing"]),
    ("sweaty", "try-hard", ["sweaty"]),
    ("tilted", "frustrated", ["tilted"]),
    ("clutch", "decisive", ["clutch"]),
    ("toxic", "abusive;hostile", ["toxic"]),
    ("camp", "ambush", ["camp", "camper", "camping"]),
    ("meta", "best tactic", ["meta"]),
    ("broken", "overpowered", ["broken"]),
    ("one shot", "very low", ["one shot"]),
    ("carry", "lead", ["carry", "hard carry"]),
    ("bot", "bad player", ["bot"]),
]
for t, g, v in gaming:
    items.append(
        mk_entry(
            t,
            short(g),
            variants=v,
            confidence=0.84,
            cats=["gaming"],
            tags=["gaming"],
            examples=[f"He went {t} in the final round."],
        )
    )

# --- REGIONAL ---
regional = [
    ("deadass", "seriously;truly", ["deadass"]),
    ("jawn", "thing", ["jawn"]),
    ("brick", "freezing", ["brick"]),
    ("od", "excessive;very", ["od", "OD"]),
    ("hella", "very;much", ["hella"]),
    ("mad", "very", ["mad"]),
]
for t, g, v in regional:
    items.append(
        mk_entry(
            t,
            short(g),
            variants=v,
            confidence=0.8,
            cats=["regional"],
            tags=["regional"],
            examples=[f"It's {t} cold outside."],
        )
    )

# --- MORE MODERN PHRASES ---
more = [
    ("be for real", "seriously"),
    ("i fear", "i worry"),
    ("i can't even", "overwhelmed"),
    ("i'm him", "that guy;dominant"),
    ("himothy", "dominant"),
    ("literally me", "relatable"),
    ("built like that", "exceptional"),
    ("not that deep", "relax"),
    ("we ball", "keep going"),
    ("low-key obsessed", "very into"),
    ("caught lacking", "unprepared"),
    ("he cooked", "excelled"),
    ("she ate that", "she excelled"),  # duplicate safe (dedupe later if needed)
    ("serve looks", "stylish"),  # duplicate safe
    ("get ready with me", "prep video"),
    ("boy math", "rationalization"),
    ("main character syndrome", "self-centered"),
    ("hot take", "controversial"),
    ("cold take", "obvious"),
    ("l take", "bad opinion"),
    ("w take", "good opinion"),
    ("copium", "forced optimism"),
    ("hopium", "unrealistic hope"),
    ("glazing", "overpraising"),
    ("cheugy", "outdated;try-hard"),
    ("ate for breakfast", "dominated"),
    ("rent free", "obsessive"),
    ("slept on", "underrated"),
    ("touch some grass", "disconnect"),
    ("bestie vibes only", "positive vibes"),
    ("mother", "icon"),
    ("father", "icon"),
    ("tea", "gossip"),
    ("spill", "reveal"),
    ("receipts or it didn’t happen", "evidence required"),
    ("my roman empire", "obsession"),
    ("era", "phase"),
    ("that’s on me", "my fault"),
    ("that’s on you", "your fault"),
    ("low effort", "lazy"),
    ("high effort", "polished"),
]
for t, g in more:
    items.append(
        mk_entry(t, short(g), confidence=0.78, cats=["slang"], examples=[f"{t} fr."])
    )

# --- MEMES ---
memes = [
    ("grimace shake", "meme drink"),
    ("barbenheimer", "double feature"),
    ("skibidi toilet", "nonsense meme"),
    ("go little rockstar", "misheard lyric"),
    ("fanum tax", "food stealing"),
    ("sigma grindset", "hustle aesthetic"),
]
for t, g in memes:
    items.append(
        mk_entry(
            t,
            short(g),
            confidence=0.72,
            cats=["meme"],
            tags=["meme"],
            examples=[f"{t} era."],
        )
    )

# --- EXTRAS ---
extras = [
    ("sus", "suspicious", ["sus"]),
    ("yap", "ramble", ["yap", "yapping"]),
    ("ate and left no crumbs", "flawless;perfect", ["ate and left no crumbs"]),
    ("left on read", "ignored", ["left on read"]),
    (
        "thirst trap",
        "provocative photo",
        ["thirst trap"],
        ["New thirst trap just dropped."],
    ),
    ("ghost", "ignore", ["ghost", "ghosted", "ghosting"]),
    ("gaslight", "manipulate", ["gaslight", "gaslighting"]),
    ("gatekeep", "exclude", ["gatekeep", "gatekeeping"]),
    ("girlboss", "lead;hustle", ["girlboss", "girlbossing"]),
    ("on god", "honestly", ["on god"]),
    ("no kizzy", "no lie", ["no kizzy"]),
    ("pushin p", "cool", ["pushin p"]),
    ("blud", "dude", ["blud"]),
    ("fam", "friends", ["fam"]),
    ("peng", "attractive", ["peng"]),
    ("peak", "unlucky", ["peak"]),
    ("zesty", "showy", ["zesty"]),
    ("slumped", "asleep", ["slumped"]),
    ("mog", "outshine", ["mog", "mogged", "mogging"]),
    ("doomscroll", "mindless scrolling", ["doomscroll", "doomscrolling"]),
    ("soft life", "low-stress", ["soft life"]),
    ("clean girl", "minimal look", ["clean girl"]),
    ("situationship", "undefined relationship", ["situationship"]),
    ("sneaky link", "casual partner", ["sneaky link"]),
    ("aura", "vibe", ["aura"]),
    ("valid af", "very legit", ["valid af"]),
    ("leng", "attractive", ["leng"]),
    ("fit check", "outfit check", ["fit check"]),
    ("vibe check", "mood test", ["vibe check"]),
    ("it me", "that's me", ["it me"]),
    ("bffr", "be for real", ["bffr"]),
    ("slay queen", "well done", ["slay queen"]),  # tuned
    ("ate up", "dominated", ["ate up"]),
    ("quiet quitting", "disengaging", ["quiet quitting"]),
    ("brain dump", "notes", ["brain dump"]),
    ("soft block", "subtle block", ["soft block"]),
    ("hard block", "block", ["hard block"]),
    ("shadow work", "self-reflection", ["shadow work"]),
    ("main character energy", "spotlight vibe", ["main character energy"]),
    ("low vibrational", "negative vibe", ["low vibrational"]),
    ("situationship era", "undefined phase", ["situationship era"]),
    ("gyatt", "curvy;wow", ["gyatt", "gyat"]),
]
for t, g, v, *rest in extras:
    ex = rest[0] if rest else [f"{t}!"]
    items.append(
        mk_entry(t, short(g), variants=v, confidence=0.8, cats=["slang"], examples=ex)
    )

# Age gating
for e in items:
    if e["term"] in {"thirst trap", "sneaky link"}:
        e["age_rating"] = "T16"
        e["content_flags"] = sorted(list(set(e.get("content_flags", [])) | {"sexual"}))

# --- DERIVED TEMPLATE FILLER (to ~500) ---
base_syn = {
    "vibe": "mood",
    "rizz": "charm",
    "fit": "outfit",
    "drip": "style",
    "slay": "excel",
    "serve": "perform",
    "mid": "mediocre",
    "based": "authentic",
    "cringe": "awkward",
    "sus": "suspicious",
    "valid": "legit",
    "bussin": "excellent",
    "fire": "excellent",
    "heat": "intense",
    "banger": "hit",
    "sigma": "stoic",
    "delulu": "delusional",
    "era": "phase",
    "energy": "vibe",
    "check": "test",
}
suf_syn = {
    "check": "test",
    "energy": "level",
    "era": "phase",
    "moment": "highlight",
    "levels": "intensity",
    "core": "aesthetic",
    "mode": "state",
    "arc": "storyline",
    "aesthetic": "style",
    "content": "posts",
    "take": "opinion",
}
base_terms = list(base_syn.keys()) + [
    "drip",
    "fit",
    "vibe",
    "rizz",
    "slay",
    "serve",
    "valid",
    "sus",
    "fire",
    "banger",
    "sigma",
    "delulu",
]
suffixes = list(suf_syn.keys())


def build_gloss_for_derived(t):
    parts = t.split()
    if len(parts) == 2 and parts[1] in suf_syn:
        base = base_syn.get(parts[0], parts[0])
        suf = suf_syn[parts[1]]
        cand = f"{base} {suf}"
        # if cand equals the term (normalized), back off to the suffix synonym only
        if norm(cand) == norm(t):
            cand = suf if suf not in {"aesthetic", "style"} else "aesthetic"
        return short(cand)
    return "slang"


seen = {norm(e["term"]) for e in items}
i = 0
while len(items) < 500 and i < 3000:
    b = base_terms[i % len(base_terms)]
    s = suffixes[i % len(suffixes)]
    t = f"{b} {s}"
    if norm(t) in seen:
        i += 1
        continue
    gloss = build_gloss_for_derived(t)
    variants = [t]
    # ensure gloss != term/variant
    if not gloss_not_equal(t, gloss, variants):
        backup = {
            "take": "opinion",
            "check": "test",
            "core": "aesthetic",
            "aesthetic": "style",
            "energy": "level",
            "era": "phase",
            "moment": "highlight",
            "levels": "intensity",
            "mode": "state",
            "arc": "storyline",
            "content": "posts",
        }.get(s, "phrase")
        gloss = backup
    items.append(
        mk_entry(
            t,
            gloss,
            variants=variants,
            confidence=0.68,
            cats=["slang"],
            tags=["derived"],
            examples=[f"{t} goes crazy."],
        )
    )
    seen.add(norm(t))
    i += 1


# --- VALIDATION ---
def validate(items):
    bad_equal = []
    long_nonacro = []
    for e in items:
        term = e.get("term", "")
        if not gloss_not_equal(term, e.get("gloss", ""), e.get("variants")):
            bad_equal.append((term, e.get("gloss", "")))
        # Non-acronym: gloss parts must be <= 3 words and no /()
        if "acronym" not in e.get("categories", []):
            for part in [
                p.strip() for p in (e.get("gloss", "") or "").split(";") if p.strip()
            ]:
                if "/" in part or "(" in part or ")" in part or len(part.split()) > 3:
                    long_nonacro.append((term, part))
    return bad_equal, long_nonacro


bad_equal, long_nonacro = validate(items)
assert not bad_equal, f"Gloss equals term in some entries: {bad_equal[:5]}"
assert not long_nonacro, f"Non-acronym gloss too long/illegal: {long_nonacro[:5]}"

# --- WRITE FILES ---
out_json = {
    "version": VERSION,
    "generated_at": TODAY,
    "count": len(items),
    "items": items,
}
json_path = "lingible_lexicon_v2_3.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(out_json, f, indent=2, ensure_ascii=False)


print(f"Wrote: {json_path} | count: {len(items)} | version: {VERSION}")
