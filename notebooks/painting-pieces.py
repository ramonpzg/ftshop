import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # Captions are the dataset

        Image fine-tuning lives or dies on captions. Build a few here and
        watch how the trigger word threads through every one.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    trigger = mo.ui.text(value="wtrclrchess", label="Trigger word")
    trigger
    return (trigger,)


@app.cell
def _(mo, trigger):
    pieces = ["white knight", "black queen", "white bishop", "black rook"]
    captions = [
        f"a {trigger.value} style {piece}, soft watercolor edges, plain background"
        for piece in pieces
    ]
    mo.md("\n".join(f"- `{caption}`" for caption in captions))
    return


@app.cell
def _(mo):
    mo.md(
        """
        The trigger word is a new token the model learns to associate with
        your style. Change it above and every caption follows. During
        training, that consistency is what binds the style to the word.

        Aspect ratios matter the same way: mixed ratios teach the model
        that your style sometimes stretches. Pick one and hold it.
        """
    )
    return


@app.cell
def _(mo):
    mo.image("/pieces/wN.svg", width=120, caption="The Cburnett knight the app ships")
    return


if __name__ == "__main__":
    app.run()
