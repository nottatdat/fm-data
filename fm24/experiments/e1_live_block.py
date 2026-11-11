#!/usr/bin/env python3
"""E1 follow-up: the live player block (order from barak14/fm-editor docs/fm24, src/fields/fm24/player.rs):
u16 CA, u16 PA, 15 position ratings (1-20), 54 attributes encoded (display = (raw+2)//5)."""
POS = ['GK', 'SW', 'DL', 'DC', 'DR', 'DM', 'ML', 'MC', 'MR', 'AML', 'AMC', 'AMR', 'ST', 'WBL', 'WBR']
ATTR = ['Crossing', 'Dribbling', 'Finishing', 'Heading', 'LongShots', 'Marking', 'OffTheBall', 'Passing',
        'PenaltyTaking', 'Tackling', 'Vision', 'Handling', 'AerialReach', 'CommandOfArea', 'Communication',
        'Kicking', 'Throwing', 'Anticipation', 'Decisions', 'OneOnOnes', 'Positioning', 'Reflexes', 'FirstTouch',
        'Technique', 'LeftFoot', 'RightFoot', 'Flair', 'Corners', 'Teamwork', 'WorkRate', 'LongThrows',
        'Eccentricity', 'RushingOut', 'Punching', 'Acceleration', 'FreeKicks', 'Strength', 'Stamina', 'Pace',
        'JumpingReach', 'Leadership', 'Dirtiness', 'Balance', 'Bravery', 'Consistency', 'Aggression', 'Agility',
        'ImportantMatches', 'InjuryProneness', 'Versatility', 'NaturalFitness', 'Determination', 'Composure',
        'Concentration']
assert len(ATTR) == 54


def disp(raw):
    return (raw + 2) // 5


def decode(b, attr_start):
    """attr_start = offset of Crossing. Returns dict."""
    import struct
    out = {a: disp(b[attr_start + i]) for i, a in enumerate(ATTR)}
    out.update({p: b[attr_start - 15 + i] for i, p in enumerate(POS)})
    out['CA'], out['PA'] = struct.unpack_from('<HH', b, attr_start - 19)
    return out


def find(b, screen, lo, hi):
    """Best attr_start in [lo, hi) by exact matches against screen {attr: value}."""
    best = (0, None)
    keys = [(ATTR.index(a), v) for a, v in screen.items() if a in ATTR]
    for s in range(lo, hi):
        e = sum(1 for i, v in keys if disp(b[s + i]) == v)
        if e > best[0]:
            best = (e, s)
    return best[0], len(keys), best[1]
