"""Regenerates the committed workshop media under artifacts/cached/media.

Run via `just make-media` (installs the `media` extra first). Every
output is deterministic: fixed seeds, no timestamps, so a regeneration
on another machine produces byte-comparable evidence, and the files can
be reviewed once and trusted offline at the venue.

What gets made and how (this docstring is the provenance record's
source of truth; docs/licenses.md summarizes it):

- image/style_before.png: the Cburnett white bishop SVG
  (web/public/pieces/wB.svg, CC BY-SA 3.0) rasterized onto plain paper.
- image/style_after.png: the same silhouette restyled programmatically
  into layered watercolor washes with edge darkening and paper grain.
  An illustrative style-transfer target, not a diffusion model output.
- audio/capture_sound.wav: a synthesized wood-on-wood capture click
  (damped noise burst plus a low thump), the sound event the audio
  page teaches. audio/capture_sound_waveform.png is its waveform.
- audio/board_music_base.wav and audio/board_music_adapted.wav: the
  same short motif twice; the adapted take is faster, tenser, and
  louder toward the end. An illustrative base-versus-adapted pair,
  synthesized locally, not model output. Waveform PNGs alongside.
- video/scene_clip.mp4 (+ scene_poster.png, scene_frames.png): a
  rendered storyboard animatic of the rushed-release incident scene
  from the video fixture: a dark operations room, a progress bar
  moving too fast, a flash, then red warning light. No chessboard, no
  chess pieces, no readable text. Encoded H.264/yuv420p via PyAV.
- video/scene_clip_base.mp4: the same scene re-rendered with per-frame
  position, tone, and progress jitter: the temporal flicker an
  unadapted checkpoint produces, as the illustrative "before" take.
  (The flicker also defeats the encoder, which is why the worse clip
  is the larger file.)
"""

import hashlib
import io
import wave
from pathlib import Path

from euro_chess_studio.config import REPO_ROOT, get_artifacts_dir

SEED = 34
IMAGE_SIZE = 768
AUDIO_RATE = 44100
VIDEO_SIZE = (640, 360)
VIDEO_FPS = 12
VIDEO_SECONDS = 8


def _out_dir(kind: str) -> Path:
    path = get_artifacts_dir() / "cached" / "media" / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


# --- image ---------------------------------------------------------------


def _paper(np, rng, size: int):
    """Warm paper: low-frequency noise over an off-white base."""
    from PIL import Image  # ty: ignore[unresolved-import]

    coarse = rng.normal(0, 1, (size // 8, size // 8))
    spread = np.ptp(coarse) + 1e-9
    grain = Image.fromarray(
        ((coarse - coarse.min()) / spread * 18).astype("uint8"), mode="L"
    ).resize((size, size), Image.Resampling.BILINEAR)
    base = Image.new("RGB", (size, size), (247, 244, 236))
    arr = np.asarray(base).astype(int) - np.asarray(grain)[..., None] // 3
    return Image.fromarray(arr.clip(0, 255).astype("uint8"))


def _piece_silhouette(size: int):
    """The Cburnett white bishop rasterized at working size."""
    import cairosvg  # ty: ignore[unresolved-import]
    from PIL import Image  # ty: ignore[unresolved-import]

    svg_path = REPO_ROOT / "web" / "public" / "pieces" / "wB.svg"
    png_bytes = cairosvg.svg2png(
        url=str(svg_path), output_width=int(size * 0.72), output_height=int(size * 0.72)
    )
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def make_image_pair() -> list[Path]:
    import numpy as np  # ty: ignore[unresolved-import]
    from PIL import Image, ImageDraw, ImageFilter  # ty: ignore[unresolved-import]

    rng = np.random.RandomState(SEED)
    out = _out_dir("image")
    piece = _piece_silhouette(IMAGE_SIZE)
    offset = ((IMAGE_SIZE - piece.width) // 2, (IMAGE_SIZE - piece.height) // 2)

    # Before: the clean render on plain paper with a soft shadow.
    before = _paper(np, rng, IMAGE_SIZE).convert("RGBA")
    shadow = Image.new("RGBA", before.size, (0, 0, 0, 0))
    alpha = piece.split()[3]
    shadow_layer = Image.new("RGBA", piece.size, (30, 30, 40, 70))
    shadow.paste(shadow_layer, (offset[0] + 14, offset[1] + 18), alpha)
    before = Image.alpha_composite(before, shadow.filter(ImageFilter.GaussianBlur(10)))
    before.paste(piece, offset, piece)
    before_path = out / "style_before.png"
    before.convert("RGB").save(before_path, optimize=True)

    # After: the same silhouette as layered watercolor washes.
    after = _paper(np, rng, IMAGE_SIZE).convert("RGBA")
    mask = Image.new("L", after.size, 0)
    mask.paste(alpha, offset)
    washes = [
        ((64, 116, 156), 16, 60),
        ((88, 148, 172), 12, 55),
        ((120, 92, 148), 10, 40),
        ((52, 96, 132), 7, 70),
        ((172, 196, 204), 20, 35),
    ]
    for color, blur, opacity in washes:
        jitter = (int(rng.randint(-10, 11)), int(rng.randint(-8, 9)))
        wash_mask = mask.transform(
            mask.size,
            Image.Transform.AFFINE,
            (1, 0, jitter[0], 0, 1, jitter[1]),
        ).filter(ImageFilter.GaussianBlur(blur))
        layer = Image.new("RGBA", after.size, (*color, 0))
        layer.putalpha(wash_mask.point(lambda p, o=opacity: p * o // 255))
        after = Image.alpha_composite(after, layer)
    # Watercolor edge darkening: the rim where pigment pools.
    edge = mask.filter(ImageFilter.MaxFilter(9))
    inner = mask.filter(ImageFilter.MinFilter(9))
    rim = np.asarray(edge).astype(int) - np.asarray(inner)
    rim_mask = Image.fromarray(rim.clip(0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(2))
    rim_layer = Image.new("RGBA", after.size, (36, 60, 92, 0))
    rim_layer.putalpha(rim_mask.point(lambda p: p * 130 // 255))
    after = Image.alpha_composite(after, rim_layer)
    # The piece's own dark linework back on top as soft ink, so the
    # mitre cross and collar band survive the washes.
    piece_arr = np.asarray(piece)
    darkness = ((255 - piece_arr[..., :3].mean(axis=2)) * (piece_arr[..., 3] / 255.0)).astype(
        "uint8"
    )
    ink_mask = Image.new("L", after.size, 0)
    ink_mask.paste(Image.fromarray(darkness), (offset[0] + 3, offset[1] + 2))
    ink_mask = ink_mask.filter(ImageFilter.GaussianBlur(1.6))
    ink_layer = Image.new("RGBA", after.size, (38, 58, 88, 0))
    ink_layer.putalpha(ink_mask.point(lambda p: p * 200 // 255))
    after = Image.alpha_composite(after, ink_layer)
    # Paint drips running off the base.
    drips = Image.new("RGBA", after.size, (0, 0, 0, 0))
    drip_draw = ImageDraw.Draw(drips)
    base_y = offset[1] + piece.height - 8
    for _ in range(3):
        x = offset[0] + int(rng.randint(piece.width // 5, piece.width * 4 // 5))
        length = int(rng.randint(36, 96))
        drip_draw.line((x, base_y, x, base_y + length), fill=(70, 118, 152, 120), width=5)
        drip_draw.ellipse(
            (x - 4, base_y + length - 4, x + 4, base_y + length + 4),
            fill=(70, 118, 152, 130),
        )
    after = Image.alpha_composite(after, drips.filter(ImageFilter.GaussianBlur(1.2)))
    grain = rng.normal(0, 5, (IMAGE_SIZE, IMAGE_SIZE, 1))
    arr = (np.asarray(after.convert("RGB")).astype(int) + grain).clip(0, 255)
    after_path = out / "style_after.png"
    Image.fromarray(arr.astype("uint8")).save(after_path, optimize=True)
    return [before_path, after_path]


# --- audio ---------------------------------------------------------------


def _write_wav(path: Path, samples) -> None:
    import numpy as np  # ty: ignore[unresolved-import]

    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(AUDIO_RATE)
        handle.writeframes(pcm.tobytes())


def _waveform_png(path: Path, samples, width: int = 800, height: int = 160) -> None:
    import numpy as np  # ty: ignore[unresolved-import]
    from PIL import Image, ImageDraw  # ty: ignore[unresolved-import]

    image = Image.new("RGB", (width, height), (250, 250, 250))
    draw = ImageDraw.Draw(image)
    mid = height // 2
    draw.line((0, mid, width, mid), fill=(210, 210, 210))
    chunks = np.array_split(samples, width)
    for x, chunk in enumerate(chunks):
        if len(chunk) == 0:
            continue
        low = int(mid - float(chunk.min()) * (mid - 6))
        high = int(mid - float(chunk.max()) * (mid - 6))
        draw.line((x, high, x, low), fill=(33, 37, 41))
    image.save(path, optimize=True)


def _tone(np, freq: float, duration: float, *, amp: float, decay: float):
    t = np.arange(int(duration * AUDIO_RATE)) / AUDIO_RATE
    envelope = np.exp(-t * decay)
    wave_sum = (
        np.sin(2 * np.pi * freq * t)
        + 0.45 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.18 * np.sin(2 * np.pi * freq * 3 * t)
    )
    return amp * envelope * wave_sum


def _render_notes(np, notes, total: float, *, amp: float, decay: float):
    track = np.zeros(int(total * AUDIO_RATE) + AUDIO_RATE)
    for start, freq, duration in notes:
        rendered = _tone(np, freq, duration, amp=amp, decay=decay)
        begin = int(start * AUDIO_RATE)
        track[begin : begin + len(rendered)] += rendered
    return track[: int(total * AUDIO_RATE)]


# D minor-ish motif as (beat, frequency, beats-held). One shared tune;
# the adapted take plays it faster with tension notes on top.
_MOTIF = [
    (0.0, 293.66, 1.0),  # D4
    (1.0, 349.23, 1.0),  # F4
    (2.0, 440.00, 1.0),  # A4
    (3.0, 392.00, 1.0),  # G4
    (4.0, 349.23, 1.0),  # F4
    (5.0, 293.66, 1.5),  # D4
    (6.5, 220.00, 1.5),  # A3
    (8.0, 293.66, 2.0),  # D4
    (10.0, 261.63, 1.0),  # C4
    (11.0, 293.66, 2.0),  # D4
]
_TENSION = [
    (2.5, 466.16, 0.5),  # Bb4 rub against A
    (4.5, 311.13, 0.5),  # Eb4 rub against D
    (6.0, 466.16, 0.5),
    (8.5, 622.25, 0.5),  # Eb5
    (9.5, 587.33, 0.5),  # D5
    (10.5, 466.16, 0.5),
    (11.5, 554.37, 0.75),  # C#5 leading tone left hanging
]


def make_audio() -> list[Path]:
    import numpy as np  # ty: ignore[unresolved-import]

    rng = np.random.RandomState(SEED)
    out = _out_dir("audio")
    paths = []

    # The capture click: a damped wooden impact.
    t = np.arange(int(0.42 * AUDIO_RATE)) / AUDIO_RATE
    burst = rng.normal(0, 1, len(t)) * np.exp(-t * 34)
    kernel = np.ones(24) / 24  # crude lowpass: wood, not glass
    burst = np.convolve(burst, kernel, mode="same")
    thump = 0.9 * np.sin(2 * np.pi * 168 * t) * np.exp(-t * 20)
    knock = 0.5 * np.sin(2 * np.pi * 620 * t) * np.exp(-t * 60)
    capture = 0.8 * (0.55 * burst + thump + knock)
    capture_path = out / "capture_sound.wav"
    _write_wav(capture_path, capture)
    _waveform_png(out / "capture_sound_waveform.png", capture)
    paths += [capture_path, out / "capture_sound_waveform.png"]

    # Base take: the motif at 90 bpm, gentle.
    beat = 60 / 90
    notes = [(s * beat, f, d * beat) for s, f, d in _MOTIF]
    base = _render_notes(np, notes, total=13 * beat, amp=0.30, decay=2.2)
    base_path = out / "board_music_base.wav"
    _write_wav(base_path, base)
    _waveform_png(out / "board_music_base_waveform.png", base)
    paths += [base_path, out / "board_music_base_waveform.png"]

    # Adapted take: the same motif at 132 bpm with tension notes,
    # tremolo, and a rising intensity envelope.
    beat = 60 / 132
    notes = [(s * beat, f, d * beat) for s, f, d in _MOTIF]
    tension = [(s * beat, f, d * beat) for s, f, d in _TENSION]
    total = 13 * beat
    adapted = _render_notes(np, notes, total=total, amp=0.30, decay=2.6)
    adapted += _render_notes(np, tension, total=total, amp=0.22, decay=5.0)
    t = np.arange(len(adapted)) / AUDIO_RATE
    tremolo = 1.0 + 0.22 * np.sin(2 * np.pi * 7.5 * t)
    # t[-1], not t.max(): identical value for an increasing arange, and
    # ndarray.max's stub overloads fail ty under some NumPy releases.
    intensity = 0.72 + 0.55 * (t / float(t[-1]))
    adapted = adapted * tremolo * intensity
    adapted_path = out / "board_music_adapted.wav"
    _write_wav(adapted_path, adapted)
    _waveform_png(out / "board_music_adapted_waveform.png", adapted)
    paths += [adapted_path, out / "board_music_adapted_waveform.png"]
    return paths


# --- video ---------------------------------------------------------------


def _scene_frame(np, rng_flicker, index: int, *, jitter_rng=None):
    """One frame of the rushed-release animatic: an operations room, a
    progress bar moving too fast, a flash, then red warning light.

    jitter_rng, when given, renders the "base checkpoint" take: every
    element's position and tone wobbles per frame, the classic temporal
    flicker an unadapted video model produces."""
    from PIL import Image, ImageDraw, ImageFilter  # ty: ignore[unresolved-import]

    def wobble(limit: int) -> int:
        if jitter_rng is None:
            return 0
        return int(jitter_rng.randint(-limit, limit + 1))

    width, height = VIDEO_SIZE
    seconds = index / VIDEO_FPS
    base_tone = 14 + wobble(6)
    image = Image.new("RGB", (width, height), (base_tone, base_tone + 3, base_tone + 10))
    draw = ImageDraw.Draw(image)

    # Wall gradient.
    for y in range(0, height, 2):
        shade = 14 + int(18 * y / height)
        draw.rectangle((0, y, width, y + 2), fill=(shade, shade + 3, shade + 9))

    # The wall screen.
    sx, sy = wobble(8), wobble(6)
    screen = (width * 0.14 + sx, height * 0.10 + sy, width * 0.86 + sx, height * 0.52 + sy)
    draw.rounded_rectangle(screen, radius=8, fill=(22, 30, 40), outline=(48, 60, 74), width=3)

    flash_start = 5.5
    if seconds < flash_start:
        progress = min(1.0, (seconds / flash_start) ** 0.8)
        if jitter_rng is not None:
            progress = max(0.0, min(1.0, progress + jitter_rng.uniform(-0.08, 0.08)))
        bar_color = (86, 176, 130) if progress < 0.85 else (196, 168, 84)
        if jitter_rng is not None:
            bar_color = tuple(
                int(min(255, max(0, c + jitter_rng.randint(-30, 31)))) for c in bar_color
            )
    else:
        progress = 1.0
        bar_color = (196, 92, 84)
    bar = (
        screen[0] + 24,
        (screen[1] + screen[3]) / 2 - 12,
        screen[0] + 24 + (screen[2] - screen[0] - 48) * progress,
        (screen[1] + screen[3]) / 2 + 12,
    )
    draw.rectangle((bar[0], bar[1], screen[2] - 24, bar[3]), fill=(30, 40, 52))
    draw.rectangle(bar, fill=bar_color)

    # Status blocks flickering on the screen edges.
    for i in range(6):
        on = rng_flicker.rand() > 0.3
        color = (60, 120, 96) if seconds < flash_start else (150, 70, 62)
        if not on:
            color = (36, 44, 54)
        x = screen[0] + 24 + i * 46
        draw.rectangle((x, screen[1] + 16, x + 30, screen[1] + 28), fill=color)

    # Desk and figure silhouettes, leaning in after the flash.
    lean = 0 if seconds < flash_start else int(6 * min(1.0, seconds - flash_start))
    desk_top = height * 0.74
    draw.rectangle((0, desk_top, width, height), fill=(9, 11, 16))
    for i, cx in enumerate((width * 0.28, width * 0.52, width * 0.74)):
        shift = (lean if i != 1 else -lean) + wobble(9)
        head = (cx - 16 + shift, desk_top - 58, cx + 16 + shift, desk_top - 26)
        body = (cx - 30 + shift, desk_top - 30, cx + 30 + shift, desk_top + 10)
        draw.ellipse(head, fill=(6, 8, 12))
        draw.rounded_rectangle(body, radius=12, fill=(6, 8, 12))

    # Flash and red pulse.
    if flash_start <= seconds < flash_start + 0.5:
        strength = 1.0 - (seconds - flash_start) / 0.5
        overlay = Image.new("RGB", image.size, (255, 250, 235))
        image = Image.blend(image, overlay, 0.75 * strength)
    elif seconds >= flash_start + 0.5:
        pulse = 0.18 + 0.12 * np.sin(2 * np.pi * 1.6 * (seconds - flash_start))
        overlay = Image.new("RGB", image.size, (120, 24, 20))
        image = Image.blend(image, overlay, float(max(0.0, pulse)))

    # Slow push-in: crop a shrinking window and scale back up.
    push = 1.0 - 0.06 * min(1.0, seconds / VIDEO_SECONDS)
    if jitter_rng is not None:
        push = min(1.0, max(0.9, push + jitter_rng.uniform(-0.012, 0.012)))
    crop_w, crop_h = int(width * push), int(height * push)
    left = (width - crop_w) // 2
    top = (height - crop_h) // 2
    image = image.crop((left, top, left + crop_w, top + crop_h)).resize(
        (width, height), Image.Resampling.LANCZOS
    )
    return image.filter(ImageFilter.GaussianBlur(0.4))


def make_video() -> list[Path]:
    import av  # ty: ignore[unresolved-import]
    import numpy as np  # ty: ignore[unresolved-import]
    from PIL import Image  # ty: ignore[unresolved-import]

    out = _out_dir("video")
    frame_count = VIDEO_FPS * VIDEO_SECONDS

    def encode(path: Path, images) -> None:
        with av.open(str(path), mode="w") as container:
            stream = container.add_stream("libx264", rate=VIDEO_FPS)
            stream.width, stream.height = VIDEO_SIZE
            stream.pix_fmt = "yuv420p"
            stream.options = {"crf": "27", "preset": "slow", "tune": "animation"}
            for frame_image in images:
                frame = av.VideoFrame.from_image(frame_image)
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)

    rng_flicker = np.random.RandomState(SEED)
    frames = [_scene_frame(np, rng_flicker, i) for i in range(frame_count)]
    clip_path = out / "scene_clip.mp4"
    encode(clip_path, frames)

    # The base-checkpoint take: same scene, per-frame temporal flicker.
    rng_flicker = np.random.RandomState(SEED)
    jitter_rng = np.random.RandomState(SEED + 1)
    base_frames = [
        _scene_frame(np, rng_flicker, i, jitter_rng=jitter_rng) for i in range(frame_count)
    ]
    base_clip_path = out / "scene_clip_base.mp4"
    encode(base_clip_path, base_frames)

    poster_path = out / "scene_poster.png"
    frames[18].save(poster_path, optimize=True)

    # Frame evidence: six uniformly sampled frames in one strip.
    sample_indices = [int(i * (frame_count - 1) / 5) for i in range(6)]
    thumb_w, thumb_h = 200, 112
    strip = Image.new("RGB", (thumb_w * 6 + 10, thumb_h + 4), (250, 250, 250))
    for slot, index in enumerate(sample_indices):
        thumb = frames[index].resize((thumb_w - 2, thumb_h), Image.Resampling.LANCZOS)
        strip.paste(thumb, (2 + slot * thumb_w, 2))
    frames_path = out / "scene_frames.png"
    strip.save(frames_path, optimize=True)
    return [clip_path, base_clip_path, poster_path, frames_path]


def main() -> None:
    paths = make_image_pair() + make_audio() + make_video()
    print("regenerated workshop media:")
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        rel = path.relative_to(get_artifacts_dir())
        print(f"  {rel}  {path.stat().st_size:>8} bytes  sha256:{digest}")


if __name__ == "__main__":
    main()
