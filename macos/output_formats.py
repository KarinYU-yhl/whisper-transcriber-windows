"""
Helpers for writing transcription output with timestamps.

Produces two files next to the input:
  - <name>.txt : one line per segment, prefixed with a [start --> end] time range
  - <name>.srt : standard SubRip subtitle file (usable as video/meeting captions)
"""


def format_timestamp(seconds, sep="."):
    """Format seconds as HH:MM:SS<sep>mmm. Use ',' for SRT, '.' for plain text."""
    if seconds is None or seconds < 0:
        seconds = 0
    ms = int(round(seconds * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{ms:03d}"


def plain_text(segments):
    """Concatenated text with no timestamps."""
    return "".join(text for _, _, text in segments).strip()


def timestamped_text(segments):
    """One line per segment: [HH:MM:SS.mmm --> HH:MM:SS.mmm] text."""
    lines = []
    for start, end, text in segments:
        lines.append(
            f"[{format_timestamp(start)} --> {format_timestamp(end)}] {text.strip()}"
        )
    return "\n".join(lines)


def build_srt(segments):
    """Build SubRip (.srt) subtitle content."""
    blocks = []
    for index, (start, end, text) in enumerate(segments, start=1):
        blocks.append(str(index))
        blocks.append(
            f"{format_timestamp(start, ',')} --> {format_timestamp(end, ',')}"
        )
        blocks.append(text.strip())
        blocks.append("")
    return "\n".join(blocks)


def write_outputs(base_path, segments):
    """Write <base_path>.txt (timestamped) and <base_path>.srt. Returns their paths."""
    txt_path = base_path + ".txt"
    srt_path = base_path + ".srt"

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(timestamped_text(segments))
        if segments:
            f.write("\n")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(build_srt(segments))

    return txt_path, srt_path
