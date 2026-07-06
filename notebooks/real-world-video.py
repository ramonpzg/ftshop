import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # Frame sampling, the whole trick

        A video model cannot eat every frame. Which ones it sees decides
        what it learns. Play with the sampling below.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    total_frames = mo.ui.slider(24, 480, value=150, step=6, label="Clip length (frames)")
    num_samples = mo.ui.slider(4, 32, value=8, step=1, label="Frames the model sees")
    mo.vstack([total_frames, num_samples])
    return num_samples, total_frames


@app.cell
def _(num_samples, total_frames):
    def uniform_frame_indices(total: int, samples: int) -> list[int]:
        if samples >= total:
            return list(range(total))
        step = total / samples
        return [int(i * step) for i in range(samples)]

    indices = uniform_frame_indices(total_frames.value, num_samples.value)
    return (indices,)


@app.cell
def _(indices, mo, total_frames):
    fps = 25
    seconds = [round(i / fps, 2) for i in indices]
    coverage = len(indices) / total_frames.value * 100
    mo.md(
        f"Sampled indices: `{indices}`\n\n"
        f"As timestamps at {fps} fps: `{seconds}`\n\n"
        f"The model sees **{coverage:.1f}%** of the clip and must hallucinate "
        "the rest coherently. That is temporal consistency, and it is why "
        "video compute escalates faster than you expect."
    )
    return


@app.cell
def _(indices, total_frames):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 1.6))
    ax.vlines(range(total_frames.value), 0, 0.3, colors="#dee2e6")
    ax.vlines(indices, 0, 1, colors="#e8590c", linewidths=2)
    ax.set_yticks([])
    ax.set_xlabel("frame index. orange = what the model sees")
    fig
    return


if __name__ == "__main__":
    app.run()
