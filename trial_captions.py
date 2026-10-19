"""Post captions for the month trial, one template per account style.

Rakia approves each template once; every post then gets its own caption filled
in from that video's brief, so the text always names what is in this video
(the character, shape or scene) and asks the viewer one question about it.
"""
import brainrot

# A few words on what each figure looks like, so a caption describes this video.
LOOKS = {
    "tung_tung_sahur": "the wooden log with a bat", "tralalero_tralala": "the shark in sneakers",
    "ballerina_cappuccina": "the cappuccino-cup ballerina", "bombardiro_crocodilo": "the crocodile bomber plane",
    "lirili_larila": "the cactus elephant in sandals", "brr_brr_patapim": "the tree monkey with big feet",
    "chimpanzini_bananini": "the chimp in a banana", "cappuccino_assassino": "the coffee-cup ninja",
    "trippi_troppi": "the shrimp cat", "boneca_ambalabu": "the tyre frog",
    "la_vaca_saturno_saturnita": "the Saturn cow", "udin_din_din_dun": "",
    "frigo_camelo": "the fridge camel", "bobrito_bandito": "the gangster beaver",
    "mario": "the plumber in the red cap", "tom": "the cat", "jerry": "the mouse",
    "glorbo_fruttodrillo": "the crocodile with a watermelon body",
    "trulimero_trulicina": "the cat-headed fish on human legs",
    "bombombini_gusini": "the flying goose with jet engines on its wings",
    "girafa_celestre": "the round green giraffe in boots",
    "il_cacto_hipopotamo": "the hippo-headed cactus in sandals",
    "ta_ta_ta_sahur": "the googly-eyed teapot on long legs",
    "orangutini_ananasini": "the orangutan with a pineapple belly and crown",
    "blueberrinni_octopussini": "the blueberry-headed baby octopus",
    "svinino_bombondino": "the pig with a hand-grenade body",
    "tigrrullini_watermellini": "the tiger with a watermelon body",
    "zibra_zubra_zibralini": "the zebra with a watermelon body",
    "spioniro_golubiro": "the spy pigeon in a trench coat and fedora",
    "burbaloni_luliloli": "the capybara inside a coconut shell",
}
FRANCHISE = {"mario": "#supermario #mario", "tom": "#tomandjerry #cartoon", "jerry": "#tomandjerry #cartoon"}
PROFILES = dict(classical="classic", soft="soft", angular="sharp", aquiline="long-nosed")
SCENES = dict(terrace="terrace of arches", mountain="mountain landscape", botanical="garden of plants")
EMOJI = dict(heart="❤️", star="⭐", crescent="🌙", butterfly="🦋", ring="⭕", leaf="🍃",
             lightning="⚡", flower="🌸", diamond="💎", hourglass="⏳")


def _tag(character):
    return "#"+"".join(ch for ch in brainrot.NAMES[character].lower() if ch.isalnum())


def _figure(character):
    look = LOOKS.get(character, "")
    return brainrot.NAMES[character]+(f", {look}," if look else "")


def caption(account, mode, p):
    if mode == "brainrot_spin" and "partner" in p:
        a, b = p["character"], p["partner"]
        tags = f"{_tag(a)} {_tag(b)} #brainrot {FRANCHISE.get(a, '#italianbrainrot')} {FRANCHISE.get(b, '#italianbrainrot')}"
        return (f"{brainrot.NAMES[a]} and {brainrot.NAMES[b]}, built from thousands of glowing particles, "
                f"spin side by side… 👀\nAre they turning the same way, or opposite ways? "
                f"Watch one, then the other, and see if one of them flips.\nComment 🔁 same or 🔀 opposite\n\n"
                + " ".join(dict.fromkeys((tags+" #opticalillusion #illusion #trustyoureyes").split())))
    if mode == "brainrot_spin":
        c = p["character"]
        return (f"{_figure(c)} built from thousands of glowing particles, spins… but which way? 👀\n"
                f"Is {brainrot.NAMES[c]} turning left or right? Blink, look again, and try to flip "
                f"the direction with your mind.\nComment ⬅️ or ➡️\n\n"
                f"{_tag(c)} #brainrot {FRANCHISE.get(c, '#italianbrainrot')} #opticalillusion #illusion #trustyoureyes")
    if mode == "depth_flip":
        return (f"A glowing wire sphere with {p['ribs']} ribs and {p['rings']} rings, open on one side, "
                f"turning in one steady direction 🌐\nAre you looking into a bowl, or at the outside of a ball? "
                f"Can you flip it in your mind?\nComment 🥣 bowl or ⚽ ball\n\n"
                f"#opticalillusion #depthillusion #illusion #brain #opticpop")
    if mode == "tilted_pair":
        a, b = p["subjects"]
        how = "circling each other" if p["layout"] == "orbit" else "spinning through each other on one axis"
        return (f"A glowing {a} and a {b}, {how} {EMOJI[a]}{EMOJI[b]}\n"
                f"Which one is in front? Follow one shape through the overlap and see if the order flips.\n"
                f"Comment {EMOJI[a]} or {EMOJI[b]}\n\n"
                f"#opticalillusion #depthillusion #illusion #brain #opticpop")
    if mode == "color_echo":
        return (f"A bright {SCENES[p['scene']]} that turns black and white after 18 seconds 🎨\n"
                f"Keep your eyes on the dot the whole time. When the colour is gone, what colours do you still see?\n"
                f"Comment the colour you saw 👇\n\n"
                f"#opticalillusion #afterimage #colorillusion #brain #hypnotorium")
    if mode == "face_flash":
        return ("Two illustrated faces flash on each side of the cross, a new pair every quarter second 👀\n"
                "Keep your eyes on the cross until the end. Do the faces start to look strange?\n"
                "Comment 😐 normal or 😱 strange\n\n"
                "#opticalillusion #flashedfaceillusion #illusion #brain #hypnotorium")
    if mode == "mirror_flip":
        return (f"Two {PROFILES[p['profile']]} profiles facing each other… or one vase? 🏺\n"
                f"Which did you see first, the faces or the vase? Can you switch between them?\n"
                f"Comment 👤 faces or 🏺 vase\n\n"
                f"#opticalillusion #rubinsvase #illusion #brain #spiralium")
    if mode == "still_wobble":
        bricks = "long, thin" if p["aspect_ratio"] >= 5 else "short"
        lay = {0: "level", 45: "diagonal"}.get(p["surround_angle"], "slanted")
        return (f"A circle of {bricks} black-and-white bricks, laid crosswise inside a {lay} brick pattern. "
                f"Every frame of this video is identical 📱\n"
                f"Gently move your phone. Does the circle in the middle float or slide?\n"
                f"Comment 🌀 it moves or 🧱 it's still\n\n"
                f"#opticalillusion #ouchiillusion #illusion #brain #spiralium")
    raise ValueError(f"no approved caption template for {account} / {mode}")


def youtube(account, mode, p):
    """Short title (<= 100 characters) and tags for the YouTube copy."""
    if mode == "brainrot_spin" and "partner" in p:
        a, b = (brainrot.NAMES[c] for c in (p["character"], p["partner"]))
        title, tags = f"Are {a} and {b} spinning the same way? #brainrot", [a, b, "brainrot", "italian brainrot"]
    elif mode == "brainrot_spin":
        name = brainrot.NAMES[p["character"]]
        title, tags = f"Which way is {name} spinning? #brainrot #illusion", [name, "brainrot", "italian brainrot"]
    elif mode == "depth_flip":
        title, tags = f"Bowl or ball? A {p['ribs']}-rib wire sphere #opticalillusion", ["depth illusion"]
    elif mode == "tilted_pair":
        a, b = p["subjects"]
        title, tags = f"The {a} or the {b}: which one is in front? #opticalillusion", ["depth illusion", a, b]
    elif mode == "color_echo":
        title, tags = f"Stare at the dot: what colour is this {SCENES[p['scene']]}? #illusion", ["afterimage", "color illusion"]
    elif mode == "face_flash":
        title, tags = "Keep your eyes on the cross: do these faces turn strange? #illusion", ["flashed face illusion"]
    elif mode == "mirror_flip":
        title, tags = f"Two {PROFILES[p['profile']]} faces, or one vase? #opticalillusion", ["rubin vase", "figure ground"]
    elif mode == "still_wobble":
        title, tags = "Does the circle move? Every frame is identical #opticalillusion", ["ouchi illusion", "motion illusion"]
    else:
        raise ValueError(f"no approved caption template for {account} / {mode}")
    return title[:100], [t.lower() for t in tags]+["optical illusion", "illusion"]
