"""
Reach-oriented captions.

Instagram allows max 5 hashtags per post, and its search now leans on
keywords in the caption text itself, so each caption has:
  1. a hook line packed with searchable words (optical illusion, brain test…)
  2. one or two lines explaining the effect (keeps people watching / rewatching)
  3. a comment prompt + a share/save prompt (the signals that push reach)
  4. exactly 5 hashtags: 2 broad, 2 niche for the style, 1 brand tag
Templates rotate by seed so consecutive posts never repeat word-for-word.
"""
import random

BRAND_TAG = "#opticpop"

STYLE = {
    "spin": {
        "hooks": [
            "Which way is the {s} spinning? 👀 Optical illusion brain test",
            "This {s} spins LEFT for some people and RIGHT for others 🌀",
            "Your brain picks the direction — optical illusion test",
            "Can you make the {s} switch direction? 🤯 Brain teaser",
        ],
        "body": [
            "It's a flat silhouette with zero depth cues, so your brain has to "
            "guess which side is in front — and it can guess either way. "
            "Watch the outlines flip it, then try switching it with your mind.",
            "Same video, two directions. Once you see it flip, try blinking or "
            "looking at the feet to switch it back.",
        ],
        "ask": [
            "Which way did you see FIRST? Comment ⬅️ or ➡️",
            "Did it switch for you? Tell me how long it took 👇",
        ],
        "tags": ["#spinningdancer", "#brainteaser", "#perception",
                 "#visualillusion", "#mindtrick"],
    },
    "stereogram": {
        "hooks": [
            "Hidden 3D image 👁️ Can you find it? Magic Eye test",
            "Only 1 in 3 people can see what's hidden here 👁️ Magic Eye",
            "There's a 3D picture inside this pattern. Can you see it?",
        ],
        "body": [
            "Bring your phone close, relax your eyes like you're looking far "
            "behind the screen, then slowly pull back until it pops out.",
            "Don't focus on the pattern — look THROUGH it. Give it 10 seconds, "
            "the answer is at the end.",
        ],
        "ask": [
            "Did you get it before the answer? No spoilers in the comments 🤫",
            "Comment what you saw (no spoilers!) 👇",
        ],
        "tags": ["#magiceye", "#stereogram", "#hiddenimage", "#eyetest",
                 "#3dart"],
    },
    "crosseye": {
        "hooks": [
            "Cross your eyes and this pops out in 3D 🤯",
            "3D without glasses 👀 Cross-eye illusion",
        ],
        "body": [
            "Slowly cross your eyes until a third picture appears between the "
            "two. Hold it there — it floats right out of the screen.",
            "Line up the two white dots by crossing your eyes. The middle "
            "image turns 3D.",
        ],
        "ask": ["Did it work for you? 👇", "First try or did it take a while?"],
        "tags": ["#crosseye", "#stereoscopic", "#3d", "#eyetest", "#3dart"],
    },
    "chromo": {
        "hooks": [
            "Is the shape floating above your screen? 🔴🔵",
            "Red and blue at different depths — color illusion",
        ],
        "body": [
            "Your eye focuses red and blue light at slightly different depths, "
            "so one color seems to hover above the other. It's called "
            "chromostereopsis. Turn your brightness up.",
        ],
        "ask": ["Which color looks closer to you? 👇",
                "Does it float for you or not at all?"],
        "tags": ["#colorillusion", "#chromostereopsis", "#eyetest",
                 "#perception", "#science"],
    },
    "blackhole": {
        "hooks": [
            "Stare at the dot until the end… then it moves on its own 🌀",
            "This picture keeps moving after it STOPS 😵 Illusion test",
        ],
        "body": [
            "It's the motion aftereffect: the neurons that detect motion get "
            "tired, so when the video stops, the opposite ones take over and "
            "the still image seems to spin backwards.",
            "Don't look away during the countdown. When it freezes, look at "
            "your hand or the wall — they'll ripple too.",
        ],
        "ask": ["Did it work on you? 👇",
                "How long did the effect last for you?"],
        "tags": ["#motionaftereffect", "#trippy", "#hypnotic", "#brainteaser",
                 "#perception"],
    },
}
STYLE["pointspin"] = {
    "hooks": [
        "Your brain decides which way {s} spins 🌀",
        "Can you reverse the spin of {s} with your mind? 🤯",
        "Left or right? {S} spins both ways — you just can't see it yet",
        "Most people can't make {s} switch direction. Can you?",
    ],
    "body": [
        "Try to reverse it with your mind. Some people switch it in seconds, "
        "others never manage it.\nTip: pretend the dots on the far side are "
        "the ones facing you.",
        "It's made only of dots with no depth cues, so your brain has to "
        "guess which side is in front. Blink, look at the edge, and try to "
        "flip it.",
        "Nothing changes in the video — the switch happens in your head. "
        "Focus on one dot near the edge and follow it.",
        "Watch it for a few seconds, then look slightly above it. For a lot "
        "of people that's the moment it suddenly reverses.",
    ],
    "ask": ["Which way did it spin for you first? ⬅️ or ➡️",
            "Did you manage to switch it? How long did it take? 👇",
            "Comment the second it flips for you 👇"],
    "tags": ["#brainteaser", "#mindtrick", "#perception", "#visualillusion",
             "#trippy"],
}
STYLE["dancer"] = STYLE["dots"] = STYLE["spin"]

SPECIAL = {
    "hidden word": {
        "hooks": ["There's a hidden word inside this cloud 👀 Can you catch it?",
                  "Pause at the right moment to read the secret message 🔍",
                  "Only sharp eyes will read what's hiding in here 👁️"],
        "body": ["For a split second all the dots line up and spell something. "
                 "Watch closely — or pause the video at the right moment.",
                 "It looks like random noise, but once per turn the dots snap "
                 "into a word. Tap and hold to pause when you see it."],
        "ask": ["Comment the word when you find it (no peeking at the "
                "comments first 🤫)",
                "What does it say? First correct answer gets pinned 📌"],
        "tags": ["#hiddenmessage", "#eyetest", "#brainteaser", "#canyouseeit",
                 "#visualillusion"],
    },
    "spin text": {
        "hooks": ["Which way is {t} spinning? 🌀",
                  "Can you make {t} spin the other way? 🤯"],
        "body": ["Same trick as the spinning dancer: no depth cues, so your "
                 "brain picks the direction. Try to flip it.",
                 "It reads backwards half the time — but which way is it "
                 "actually turning? Your brain decides."],
        "ask": ["Want YOUR name spinning next? Comment it below 👇",
                "Drop your name in the comments and we'll make it spin 👇"],
        "tags": ["#yourname", "#brainteaser", "#mindtrick", "#perception",
                 "#visualillusion"],
    },
}
SUBJECT = {"rainbow sphere": "this rainbow sphere", "arrow band": "this arrow loop",
           "crown": "this crown of lights", "dark star": "this red planet",
           "arrow ring": "this arrow ring", "cube": "this cube",
           "DNA helix": "this DNA", "planet": "this planet"}

FOLLOW = "Follow @opticpop for a new illusion every day ✨"
SHARE = [
    "Send this to a friend and see if they see it the same way 👀",
    "Save it and try it again later — it changes 🔁",
    "Tag someone who needs to try this",
    "Share it with someone who says illusions don't work on them",
]
BROAD = ["#opticalillusion", "#illusion"]


def build(style, subject, seed, text=None):
    r = random.Random(seed)
    if subject in SPECIAL:
        sp = SPECIAL[subject]
        t = (text or "OPTICPOP").replace("\n", " ")
        hook = r.choice(sp["hooks"]).format(t=t)
        tags = BROAD + r.sample(sp["tags"], 2) + [BRAND_TAG]
        return (f"{hook}\n\n{r.choice(sp['body'])}\n\n{r.choice(sp['ask'])}\n"
                f"{FOLLOW}\n\n{' '.join(tags)}"), tags
    s = STYLE[style]
    subj = "dancer" if subject.startswith("ballerina") else subject
    if subj in ("sphere", "cylinder", "torus", "helix"):
        subj = subj if style != "dots" else f"{subj} of dots"
    if style == "pointspin":
        subj = SUBJECT.get(subject, "this shape")
    hook = r.choice(s["hooks"]).format(s=subj, S=subj[:1].upper() + subj[1:])
    tags = BROAD + r.sample(s["tags"], 2) + [BRAND_TAG]
    cta = FOLLOW if style == "pointspin" else r.choice(SHARE)
    text = (f"{hook}\n\n{r.choice(s['body'])}\n\n{r.choice(s['ask'])}\n"
            f"{cta}\n\n{' '.join(tags)}")
    return text, tags


# ------------------------------------------------------------------ short
# Reels show only ~1 line (about 50-55 characters, depends on the phone)
# before "more", and a line break cuts it off earlier. Short captions are a
# single line that fits entirely in that space.
SHORT_LIMIT = 52
SHORT_HOOKS = {
    "pointspin": ["Reverse the spin with your mind 🌀",
                  "Which way is it spinning? 🌀",
                  "Can you make it spin the other way?",
                  "Left or right? Your brain decides 🌀",
                  "Most people can't flip this one 🤯",
                  "Make it switch direction 🌀"],
    "hidden word": ["Pause it to read the hidden word 👀",
                    "Find the hidden word 👀",
                    "There's a word in here. Find it 🔍"],
    "spin text": ["Which way is it spinning? 🌀",
                  "Comment your name, we'll spin it 🌀"],
}
SHORT_TAGS = ["#opticalillusion", "#illusion", "#brainteaser", "#opticpop"]


def build_short(style, subject, seed):
    """Hook on one short line (fully visible before 'more'), then the five
    hashtags on their own lines: hidden behind 'more' but still indexed."""
    r = random.Random(seed)
    hooks = SHORT_HOOKS.get(subject) or SHORT_HOOKS["pointspin"]
    hook = r.choice(hooks)
    pool = (SPECIAL.get(subject) or STYLE.get(style) or STYLE["pointspin"])
    tags = BROAD + r.sample(pool["tags"], 2) + [BRAND_TAG]
    return f"{hook}\n.\n{' '.join(tags)}"
