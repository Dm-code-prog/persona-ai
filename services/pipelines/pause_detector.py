import copy


def detect_pauses(words, threshold=0.5, pad=0.1):
    words = copy.deepcopy(words)
    pauses = []

    # 1) Identify all pauses (in the original timeline)
    for i in range(len(words) - 1):
        gap = words[i + 1]['start'] - words[i]['end']
        if gap >= threshold:
            pause_start = words[i]['end'] + pad
            pause_end = words[i + 1]['start'] - pad
            if pause_end > pause_start:
                pauses.append({"start": pause_start, "end": pause_end})

    # 2) Sort the pauses by their start time
    pauses.sort(key=lambda p: p['start'])

    # 3) Single pass to shift
    total_shift = 0.0
    for pause in pauses:
        start = pause['start'] - total_shift
        end = pause['end'] - total_shift
        length = end - start

        # Shift subsequent words
        for w in words:
            if w['start'] >= end:
                w['start'] -= length
                w['end'] -= length

        total_shift += length

    return words, pauses
