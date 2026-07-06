import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # Sound as image

        Synthesize a capture click, then look at it the way an audio model
        does: as a spectrogram, which is to say, as a picture.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import numpy as np

    sample_rate = 16000
    duration = mo.ui.slider(0.1, 1.0, value=0.3, step=0.1, label="Click duration (s)")
    duration
    return duration, np, sample_rate


@app.cell
def _(duration, np, sample_rate):
    t = np.linspace(0, duration.value, int(sample_rate * duration.value), endpoint=False)
    # A wooden click: a sharp attack, fast decay, two resonant modes.
    envelope = np.exp(-t * 30)
    wave = envelope * (0.7 * np.sin(2 * np.pi * 820 * t) + 0.3 * np.sin(2 * np.pi * 1750 * t))
    return (wave,)


@app.cell
def _(mo, sample_rate, wave):
    import io
    import wave as wave_module

    import numpy as np2

    buffer = io.BytesIO()
    with wave_module.open(buffer, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes((wave * 32767).astype(np2.int16).tobytes())
    mo.audio(buffer.getvalue())
    return


@app.cell
def _(sample_rate, wave):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.specgram(wave, Fs=sample_rate, NFFT=256, noverlap=128)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("frequency (Hz)")
    ax.set_title("The same click, as the picture a model trains on")
    fig
    return


if __name__ == "__main__":
    app.run()
