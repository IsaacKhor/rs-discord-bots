from datetime import date, datetime, timezone
from typing import *

# ==========================
# === Vis wax calculator ===
# ==========================


def java_lcg_next_int(seed, n, repeats=1):
    multiplier = 0x5DEECE66D
    mask = (1 << 48) - 1
    addend = 0xB
    seed = (seed ^ multiplier) & mask
    for i in range(repeats):
        seed = (seed * multiplier + addend) & mask
    seed = (seed >> 17)
    # is power of 2
    if (n & (n-1) == 0):
        return int(seed * n // 2**31)
    slot = seed % n
    return slot


slots = ['Air', 'Water', 'Earth', 'Fire', 'Dust', 'Lava', 'Mist', 'Mud', 'Smoke', 'Steam',
         'Mind', 'Body', 'Cosmic', 'Chaos', 'Nature', 'Law', 'Death', 'Astral', 'Blood', 'Soul']
rune_ids = list(range(554, 554+20))

# (multiplier, final_offset) pairs
slot2_params = [(2, -2), (3, -1), (4, 2)]


def predict(runedate: int):
    slot1scores = [None for _ in range(20)]
    slot1best = java_lcg_next_int(2**32 * runedate, 19)
    slot1scores[slot1best] = 30
    used = set()
    for offset in range(1, 20):
        score = java_lcg_next_int(2**32 * runedate + 1, 29, repeats=offset+1)+1
        while score in used:
            score = (score+1) % 29
        slot1scores[(slot1best + offset) % 20] = score
        used.add(score)

    slot2scores = []
    for i in range(3):
        slot2subscores = [None for _ in range(20)]
        multiplier, final_offset = slot2_params[i]
        slot2best = (java_lcg_next_int(multiplier * 2 **
                     32 * runedate, 19) + final_offset) % 19
        if slot2best == slot1best:
            slot2best += 1  # TODO: what does this actually do with the starting point for the alts?
        slot2subscores[slot2best] = 30
        used = set()
        for offset in range(1, 20):
            score = java_lcg_next_int(
                multiplier * 2**32 * runedate + multiplier, 29, repeats=offset+1)+1
            while score in used:
                score = (score+1) % 29
            slot2subscores[(slot2best + offset) % 20] = score
            used.add(score)
        slot2scores.append(slot2subscores)

    return slot1scores, slot2scores


def runedate_today() -> int:
    rd_start = date(2002, 2, 27)
    rd_today = datetime.now(timezone.utc).date()
    delta = rd_today - rd_start
    return delta.days


def label_slots(predicted: List[int]) -> List[List[Tuple[int, str]]]:
    s1 = [(predicted[0][i], slots[i]) for i in range(20)]
    s2a = [(predicted[1][0][i], slots[i]) for i in range(20)]
    s2b = [(predicted[1][1][i], slots[i]) for i in range(20)]
    s2c = [(predicted[1][2][i], slots[i]) for i in range(20)]
    return [s1, s2a, s2b, s2c]


def str_of_slot(t: List[Tuple[int, str]]) -> str:
    pair_strs = [f'{x[0]} {x[1]}' for x in t]
    return ', '.join(pair_strs)


def slot_messages():
    runedate = runedate_today()
    predicted = predict(runedate)
    labeled = label_slots(predicted)
    top = [sorted(x, reverse=True)[:6] for x in labeled]
    to_str = [str_of_slot(x) for x in top]
    slot_msgs = f'Slot 1: {to_str[0]}\nSlot 2a: {to_str[1]}\nSlot 2b: {to_str[2]}\nSlot 2c: {to_str[3]}'
    return slot_msgs
