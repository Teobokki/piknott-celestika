"""PIKNOTT CELESTIKA data: types, moves, species, stats, catching and damage maths. All names/designs are original."""
import random, math

TYPES = ["Plain", "Spark", "Leaf", "Aqua", "Ember", "Stone", "Frost", "Shade", "Sky"]
TYPE_COL = {"Plain": (0.80, 0.78, 0.72), "Spark": (1.00, 0.85, 0.15), "Leaf": (0.40, 0.80, 0.30), "Aqua": (0.25, 0.60, 1.00),
            "Ember": (1.00, 0.42, 0.18), "Stone": (0.62, 0.52, 0.40), "Frost": (0.65, 0.92, 1.00), "Shade": (0.48, 0.32, 0.70),
            "Sky": (0.55, 0.80, 0.98)}
# attacker -> {defender: multiplier}
CHART = {
    "Spark": {"Aqua": 2, "Sky": 2, "Leaf": 0.5, "Stone": 0.5, "Spark": 0.5},
    "Leaf": {"Aqua": 2, "Stone": 2, "Ember": 0.5, "Sky": 0.5, "Leaf": 0.5},
    "Aqua": {"Ember": 2, "Stone": 2, "Leaf": 0.5, "Aqua": 0.5},
    "Ember": {"Leaf": 2, "Frost": 2, "Aqua": 0.5, "Stone": 0.5, "Ember": 0.5},
    "Stone": {"Ember": 2, "Sky": 2, "Frost": 2, "Leaf": 0.5},
    "Frost": {"Leaf": 2, "Sky": 2, "Ember": 0.5, "Aqua": 0.5, "Frost": 0.5},
    "Shade": {"Shade": 2, "Plain": 0.5, "Spark": 2},
    "Sky": {"Leaf": 2, "Spark": 0.5, "Stone": 0.5},
    "Plain": {"Stone": 0.5, "Shade": 0.5},
}


def effectiveness(mtype, def_types):
    m = 1.0
    for t in def_types:
        m *= CHART.get(mtype, {}).get(t, 1.0)
    return m


# name: (type, power, accuracy, pp, kind)   kind: "hit" | "heal" | "boost"
MOVES = {
    "Tackle Hop": ("Plain", 40, 100, 30, "hit"), "Quick Swipe": ("Plain", 45, 100, 25, "hit"),
    "Body Slam": ("Plain", 75, 90, 12, "hit"), "Rest Glow": ("Plain", 0, 100, 8, "heal"), "Focus Up": ("Plain", 0, 100, 10, "boost"),
    "Static Nip": ("Spark", 40, 100, 25, "hit"), "Volt Dash": ("Spark", 60, 95, 18, "hit"), "Thunder Burst": ("Spark", 90, 85, 8, "hit"),
    "Leaf Flick": ("Leaf", 40, 100, 25, "hit"), "Vine Lash": ("Leaf", 60, 95, 18, "hit"), "Bloom Cannon": ("Leaf", 90, 85, 8, "hit"),
    "Splash Jet": ("Aqua", 40, 100, 25, "hit"), "Tide Slam": ("Aqua", 65, 95, 15, "hit"), "Torrent": ("Aqua", 90, 85, 8, "hit"),
    "Ember Spit": ("Ember", 40, 100, 25, "hit"), "Flame Rush": ("Ember", 65, 95, 15, "hit"), "Magma Roar": ("Ember", 95, 85, 8, "hit"),
    "Pebble Toss": ("Stone", 40, 100, 25, "hit"), "Rock Crush": ("Stone", 70, 90, 15, "hit"), "Landslide": ("Stone", 95, 80, 8, "hit"),
    "Frost Breath": ("Frost", 40, 100, 25, "hit"), "Ice Shard": ("Frost", 60, 100, 18, "hit"), "Blizzard Veil": ("Frost", 90, 85, 8, "hit"),
    "Shadow Peck": ("Shade", 40, 100, 25, "hit"), "Night Veil": ("Shade", 65, 95, 15, "hit"), "Void Pulse": ("Shade", 90, 85, 8, "hit"),
    "Gust Wing": ("Sky", 40, 100, 25, "hit"), "Air Slice": ("Sky", 65, 95, 15, "hit"), "Star Dive": ("Sky", 95, 85, 8, "hit"),
}

# id, name, types, base stats (hp, atk, def, spd), moves, catch rate, base xp, zones, size, aggressive, dex text, model recipe
SPECIES = [
    dict(id=1, name="Lumibun", types=["Spark"], base=(45, 52, 40, 70), moves=["Quick Swipe", "Static Nip", "Volt Dash", "Thunder Burst"],
         rate=0.45, xp=60, zones=["Starter Meadow"], size=0.75, aggro=False, model="rabbit", col=(1.0, 0.86, 0.12), col2=(1.0, 0.95, 0.65),
         text="A bright yellow hare that stores starlight in its long ears. It watches the volcano for hours."),
    dict(id=2, name="Sproutle", types=["Leaf"], base=(48, 45, 52, 45), moves=["Tackle Hop", "Leaf Flick", "Vine Lash", "Rest Glow"],
         rate=0.6, xp=50, zones=["Starter Meadow", "Ink Forest"], size=0.6, aggro=False, model="blob", col=(0.45, 0.80, 0.35), col2=(0.95, 0.85, 0.55),
         text="A round seedling that naps in tall grass. The leaf on its head turns to follow the sun."),
    dict(id=3, name="Puddlop", types=["Aqua"], base=(55, 45, 50, 40), moves=["Tackle Hop", "Splash Jet", "Tide Slam", "Rest Glow"],
         rate=0.6, xp=50, zones=["Mirror Lake", "Starter Meadow"], size=0.65, aggro=False, model="frog", col=(0.30, 0.62, 1.0), col2=(0.85, 0.95, 1.0),
         text="A jelly-soft frog that bounces between lily pads. It hums when it rains."),
    dict(id=4, name="Cindercub", types=["Ember"], base=(46, 60, 40, 62), moves=["Quick Swipe", "Ember Spit", "Flame Rush", "Focus Up"],
         rate=0.45, xp=62, zones=["Rocky Ridge", "Ash Slopes"], size=0.75, aggro=True, model="fox", col=(0.95, 0.38, 0.16), col2=(1.0, 0.85, 0.40),
         text="A hot-tempered cub with a flickering tail. It charges anyone who wanders too close."),
    dict(id=5, name="Pebbit", types=["Stone"], base=(50, 55, 70, 25), moves=["Tackle Hop", "Pebble Toss", "Rock Crush", "Focus Up"],
         rate=0.55, xp=55, zones=["Rocky Ridge"], size=0.7, aggro=False, model="beetle", col=(0.55, 0.50, 0.46), col2=(0.85, 0.62, 0.30),
         text="A beetle whose shell is a polished pebble. Piles of them look exactly like rocks."),
    dict(id=6, name="Gloomoth", types=["Shade"], base=(45, 50, 45, 65), moves=["Quick Swipe", "Shadow Peck", "Night Veil", "Gust Wing"],
         rate=0.45, xp=60, zones=["Ink Forest"], size=0.75, aggro=False, model="moth", col=(0.35, 0.28, 0.52), col2=(0.85, 0.80, 1.0),
         text="A moth with ink-drop wings. Its glowing eye spots scare off anything that stares."),
    dict(id=7, name="Zephlit", types=["Sky"], base=(42, 50, 38, 80), moves=["Quick Swipe", "Gust Wing", "Air Slice", "Star Dive"],
         rate=0.45, xp=58, zones=["Rocky Ridge", "Starter Meadow"], size=0.6, aggro=False, model="bird", col=(0.55, 0.82, 1.0), col2=(1.0, 1.0, 1.0),
         text="A swift little bird that rides mountain winds. It sings two notes, never three."),
    dict(id=8, name="Tidefin", types=["Aqua"], base=(60, 62, 55, 60), moves=["Body Slam", "Splash Jet", "Tide Slam", "Torrent"],
         rate=0.3, xp=90, zones=["Mirror Lake"], size=1.0, aggro=False, model="fish", col=(0.15, 0.45, 0.80), col2=(0.90, 0.95, 1.0),
         text="A big-finned swimmer that leaps from Mirror Lake at dusk, splashing everything nearby."),
    dict(id=9, name="Voltail", types=["Spark"], base=(44, 56, 42, 75), moves=["Quick Swipe", "Static Nip", "Volt Dash", "Air Slice"],
         rate=0.4, xp=65, zones=["Ink Forest", "Starter Meadow"], size=0.65, aggro=True, model="squirrel", col=(0.30, 0.30, 0.38), col2=(1.0, 0.90, 0.20),
         text="A dark squirrel with a lightning-yellow tail. It zaps first and asks questions never."),
    dict(id=10, name="Mossmane", types=["Leaf", "Stone"], base=(75, 75, 72, 45), moves=["Body Slam", "Vine Lash", "Rock Crush", "Bloom Cannon"],
         rate=0.18, xp=140, zones=["Ink Forest"], size=1.4, aggro=True, model="lion", col=(0.45, 0.55, 0.42), col2=(0.25, 0.55, 0.22),
         text="The guardian of the Ink Forest. Moss and stones grow in its huge mane."),
    dict(id=11, name="Frostfawn", types=["Frost"], base=(55, 55, 55, 70), moves=["Quick Swipe", "Frost Breath", "Ice Shard", "Blizzard Veil"],
         rate=0.3, xp=100, zones=["Snowline"], size=1.0, aggro=False, model="deer", col=(0.85, 0.94, 1.0), col2=(0.45, 0.75, 1.0),
         text="A shy fawn with crystal antlers that only lives near the snowy peak of Celestika."),
    dict(id=12, name="Magmaul", types=["Ember", "Stone"], base=(80, 85, 80, 35), moves=["Body Slam", "Flame Rush", "Rock Crush", "Magma Roar"],
         rate=0.15, xp=150, zones=["Ash Slopes"], size=1.5, aggro=True, model="golem", col=(0.30, 0.25, 0.25), col2=(1.0, 0.50, 0.12),
         text="A lumbering boulder beast with lava veins. The ground shakes as it stomps."),
    dict(id=13, name="Astralynx", types=["Shade", "Sky"], base=(90, 95, 85, 95), moves=["Night Veil", "Air Slice", "Void Pulse", "Star Dive"],
         rate=0.05, xp=250, zones=["Summit"], size=1.4, aggro=True, model="lynx", col=(0.12, 0.14, 0.32), col2=(0.55, 0.95, 1.0),
         text="A legendary lynx made of night sky. Legends say it guards the crater of Celestika Volcano."),
]
BY_ID = {s["id"]: s for s in SPECIES}
BY_NAME = {s["name"]: s for s in SPECIES}

BALLS = [  # key, display, catch multiplier, colour
    ("pikcel", "Pikcel Ball", 1.0, (0.20, 0.62, 0.98)),
    ("nova", "Nova Pikcel", 1.6, (0.62, 0.30, 0.95)),
    ("astral", "Astral Pikcel", 2.4, (0.95, 0.80, 0.30)),
]
STYLES = {"Normal": (1.0, 1.0), "Strong": (1.45, 1.55), "Agile": (0.65, 0.55)}   # power mult, action-time mult


def xp_for(level):
    return int(0.8 * level ** 3)


class Mon:
    def __init__(self, sid, level, nick=None):
        self.sid = sid; self.level = level; self.xp = xp_for(level)
        self.atk_boost = 0
        self.recalc(); self.hp = self.maxhp
        self.pp = {m: MOVES[m][3] for m in self.sp["moves"]}

    @property
    def sp(self):
        return BY_ID[self.sid]

    @property
    def name(self):
        return self.sp["name"]

    @property
    def types(self):
        return self.sp["types"]

    def recalc(self):
        hp, a, d, s = self.sp["base"]; L = self.level
        old = getattr(self, "maxhp", None)
        self.maxhp = int(2 * hp * L / 100) + L + 10
        self.atk = int(2 * a * L / 100) + 5
        self.dfn = int(2 * d * L / 100) + 5
        self.spd = int(2 * s * L / 100) + 5
        if old is not None:
            self.hp = min(self.maxhp, self.hp + (self.maxhp - old))

    def gain_xp(self, n):
        """Returns list of levels reached."""
        self.xp += n; ups = []
        while self.level < 100 and self.xp >= xp_for(self.level + 1):
            self.level += 1; self.recalc(); ups.append(self.level)
        return ups

    def heal_full(self):
        self.hp = self.maxhp; self.atk_boost = 0
        self.pp = {m: MOVES[m][3] for m in self.sp["moves"]}

    def to_json(self):
        return {"sid": self.sid, "level": self.level, "xp": self.xp, "hp": self.hp, "pp": self.pp}

    @staticmethod
    def from_json(d):
        m = Mon(d["sid"], d["level"]); m.xp = d.get("xp", m.xp); m.hp = min(m.maxhp, d.get("hp", m.maxhp))
        for k, v in d.get("pp", {}).items():
            if k in m.pp:
                m.pp[k] = v
        return m


def damage(att, dfn, move, style="Normal"):
    mtype, power, acc, pp, kind = MOVES[move]
    eff = effectiveness(mtype, dfn.types)
    stab = 1.5 if mtype in att.types else 1.0
    a = att.atk * (1 + 0.5 * att.atk_boost)
    base = ((2 * att.level / 5 + 2) * power * STYLES[style][0] * a / max(1, dfn.dfn)) / 50 + 2
    dmg = max(1, int(base * stab * eff * random.uniform(0.85, 1.0)))
    return dmg, eff


def action_time(mon, style="Normal"):
    """Legends-Arceus-like action cost: faster PIKNOTT and Agile style act sooner, Strong acts later."""
    return 100.0 * 80.0 / (mon.spd + 30.0) * STYLES[style][1]


def catch_chance(mon, ball_mult, stealth=1.0, in_battle=False):
    sp = mon.sp
    hp_f = 1.0 - 0.66 * mon.hp / mon.maxhp
    lvl_f = max(0.5, 1.0 - mon.level / 120.0)
    c = sp["rate"] * ball_mult * hp_f * lvl_f * stealth * (1.1 if in_battle else 1.0) * 1.6
    return max(0.02, min(0.97, c))
