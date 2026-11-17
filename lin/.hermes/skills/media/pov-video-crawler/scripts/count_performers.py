#!/usr/bin/env python3
"""Count videos per performer using 3-strategy filename matching.

Usage: python3 scripts/count_performers.py [--uncategorized]

Scans /mnt/storage/videos/ using 3 cleaning strategies (raw, underscore→space, dot→space)
and matches against known performers. Reports matched counts and uncategorized files.
"""

import re
from collections import defaultdict
from pathlib import Path

VIDEOS_DIR = Path("/mnt/storage/videos")

PERFORMER_PATTERNS = {
    "Mia Malkova": ["mia malkova", "mia_malkova", "mia-malkova", "miamalkova"],
    "Kali Roses": ["kali r", "kali_rose", "kali rose", "kali_roses"],
    "Aleksa Mink": ["aleksa", "aleska mink"],
    "Tru Kait": ["tru kait", "tru_kait", "trukait", "eporner_so_tru"],
    "Lena Paul": ["lena paul", "lena_paul"],
    "Lana Rhoades": ["lana rhoades", "lana_rhoades", "lana rhoads", "l4n4", "busty lana", "lana caught", "lr ppv"],
    "Lauren Phillips": ["lauren phillips", "lauren_phillips"],
    "Payton Preslee": ["payton preslee", "payton_preslee"],
    "Asa Akira": ["asa akira", "asa_akira", "asa does pov"],
    "Lexi Luna": ["lexi luna", "lexi_luna", "milf lexi"],
    "Angela White": ["angela white", "angela_white"],
    "Siri Dahl": ["siri dahl", "siri_dahl"],
    "Natasha Nice": ["natasha nice", "natasha_nice"],
    "Kimmy Granger": ["kimmy granger", "kimmy_granger"],
    "Ember Snow": ["ember snow", "ember_snow"],
    "Richelle Ryan": ["richelle", "miss ryan"],
    "Violet Myers": ["violet myers", "violet_myers", "violet.myers"],
    "Blake Blossom": ["blake blossom", "bl4k3", "blak3"],
    "Karma RX": ["karma rx", "karma_rx", "k4rm4rx"],
    "Sophie Dee": ["sophie dee", "sophie_dee"],
    "Riley Reid": ["riley reid", "riley_reid", "riley%20reid"],
    "Alanna Pow": ["alanna pow", "alanna_pow"],
    "Sky Bri": ["sky bri", "sky_bri"],
    "Angie Faith": ["angie faith", "angie_faith"],
    "Blondie Fesser": ["blondie fesser", "blondie_fesser", "blondie_"],
    "Rissa May": ["rissa may", "rissa_may"],
    "Ava Nicks": ["ava nicks", "ava_nicks"],
    "Nicole Doshi": ["nicole doshi", "nicole_doshi", "nicole.doshi"],
    "Vivian Taylor": ["vivian taylor", "vivian_taylor"],
    "Mia Melano": ["mia melano", "mia_melano", "miamelano"],
    "Kendra Sunderland": ["kendra sunderland", "kendra_sunderland"],
    "Sharon Lee": ["sharon lee", "sharon_lee", "sharon l33"],
    "Jade Kush": ["jade kush", "jade_kush"],
    "Lulu Chu": ["lulu chu", "lulu_chu"],
    "Ava Addams": ["ava addams", "ava_addams"],
    "Lily Lane": ["lily lane", "lily_lane"],
    "Dan Dangler": ["dan dangler", "dan_dangler", "thedandangler", "dd_"],
    "Camila Herrera7": ["camila herrera"],
    "Camila Mendez": ["camila mendez"],
    "Savannah Bond": ["savannah bond", "savannah_bond"],
    "Eva Lovia": ["eva lovia", "eva_lovia"],
    "Alyx Star": ["alyx star"],
    "Braylin Bailey": ["braylin"],
    "Camila Cortez": ["camila cortez"],
    "Kazumi": ["kazumi"],
    "Violet Starr": ["violet starr"],
    "Morgan Lee": ["morgan lee"],
    "Alina Li": ["alina li"],
    "Camila Castillo": ["camila castillo"],
    "Nikki Brooks": ["nikki brooks"],
    "Lanie Morgan": ["lanie morgan"],
    "Mia Khalifa": ["mia khalifa"],
    "Nova Cane": ["nova cane"],
    "Alva Jay": ["alva jay"],
    "Skylar Vox": ["skylar vox"],
    "Hailey Rose": ["hailey rose"],
    "Ava Sinclaire": ["ava sinclaire"],
    "Octokuro": ["octokuro"],
    "Abigaiil Morris": ["abigaiil"],
    "Elly Clutch": ["elly clutch"],
    "Kylie Rocket": ["kylie rocket"],
    "Nina Elle": ["nina elle", "nina_elle"],
    "Pristine Edge": ["pristine edge", "pristine_edge"],
    "Comatozze": ["comatozze"],
    "Alaskaclarke": ["alaskaclarke"],
    "Minami Airi": ["minamiairi"],
    "Johnny Sins": ["johnny sins"],
    "Nagi Hikaru": ["nagi hikaru", "hikaru nagi"],
    "Marcx": ["marcx"],
    "Himari": ["himari"],
    "Kate Kuray": ["kate kuray"],
    "SashaCurves": ["sashacurves"],
    "Arabelle Raphael": ["arabelle"],
    "Skyla Novea": ["skyla.novea"],
    "Linzee Ryder": ["linzee ryder", "linzee_ryder"],
    "Little Puck": ["little puck"],
    "K. Grey": ["k.grey"],
    "Brandy Renee": ["brandy renee"],
    "Sophia Weber": ["sofia weber"],
    "Nicole Murkovski": ["nicole murkovski"],
    "Victoria Lobov": ["victoria lobov", "victoria.lobov"],
    "WettMelons": ["wettmelons"],
    "Kate Dee": ["kate dee", "kate_dee"],
    "Angel Youngs": ["angel-youngs"],
    "Jade Hutchison": ["jade hutchison"],
    "Linda Lan": ["linda lan"],
    "Lani Rivers": ["lani rivers", "lanirivers"],
    "Louisa Rain": ["louisa rain"],
    "Atlanta Moreno": ["atlanta moreno", "am_"],
    "Ella Knox": ["ella knox"],
    "Bubblebratz": ["bubblebratz"],
    "Ava Adams": ["ava adams"],
    "Lexi Belle": ["lexi belle"],
    "Rion": [" rion"],
}


def main():
    counts = defaultdict(int)
    uncategorized = []

    for f in VIDEOS_DIR.iterdir():
        if f.suffix.lower() not in ['.mp4', '.webm', '.mkv'] or f.name.startswith('.'):
            continue
        name_lower = f.stem.lower()
        name_clean1 = re.sub(r'\s*\[[a-zA-Z0-9_-]+\]', '', name_lower)
        name_clean2 = name_lower.replace('_', ' ')
        name_clean3 = name_lower.replace('.', ' ')

        found = False
        for perf, patterns in PERFORMER_PATTERNS.items():
            for p in patterns:
                if p in name_lower or p in name_clean1 or p in name_clean2 or p in name_clean3:
                    counts[perf] += 1
                    found = True
                    break
            if found:
                break

        if not found:
            uncategorized.append(f.name)

    sorted_counts = sorted(counts.items(), key=lambda x: -x[1])
    total_matched = sum(c for _, c in sorted_counts)

    print(f"Total videos: {total_matched + len(uncategorized)}")
    print(f"Matched: {total_matched}")
    print(f"Uncategorized: {len(uncategorized)}")
    print()

    for name, c in sorted_counts:
        print(f"  {name:<25} {c:>3}")

    import sys
    if '--uncategorized' in sys.argv:
        print(f"\nUncategorized ({len(uncategorized)}):")
        for fn in sorted(uncategorized):
            print(f"  {fn}")


if __name__ == "__main__":
    main()
