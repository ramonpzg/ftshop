---
footer: false
class: part-opener
---

<div class="part-number">4</div>
<div class="part-title">The chess objects, after we have seen them</div>
<div class="part-sub">Names for what you already watched.</div>

<!--
TIMING: 15 seconds.
SAY: The recap comes late on purpose. You have seen the game; now you get names for what happened.
CLICK: none.
SOURCE: none.
CUT: never.
FALLBACK: static.
-->

---
clicks: 3
---

# The rules the workshop needs

<div class="rules-grid">
<ChessBoard fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" size="270px" />
<div class="rules-list">
  <div v-click="1" class="reserve rule-group">
    <span class="rule-name">Turns and legal moves</span>
    <span>White moves, Black moves. Every piece has a fixed move set; the
    position decides which moves are legal.</span>
  </div>
  <div v-click="2" class="reserve rule-group">
    <span class="rule-name">Check and checkmate</span>
    <span>Attack the king: check. No legal escape: checkmate, game over.</span>
  </div>
  <div v-click="3" class="reserve rule-group">
    <span class="rule-name">Captures, promotion, castling</span>
    <span>Land on a piece to take it. A pawn reaching the last rank becomes
    another piece. King and rook can make one special joint move.</span>
  </div>
</div>
</div>

<style>
.rules-grid {
  display: grid;
  grid-template-columns: 270px 1fr;
  gap: 2.5rem;
  align-items: start;
  margin-top: 0.3rem;
}
.rule-group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.55rem 0;
}
.rule-name {
  font-weight: 600;
}
.rule-group span:last-child {
  font-size: 0.9rem;
  color: var(--ink-soft);
}
</style>

<!--
TIMING: 2 minutes.
SAY: Only what the rest of the workshop needs. En passant lives in the notebook, or comes up if someone asks.
CLICK: 3. Turns and legality, check and mate, then captures, promotion, castling.
SOURCE: board rendered locally from the start position.
CUT: never for a mixed room; compress hard for a chess-heavy one.
FALLBACK: static board, no dependencies.
-->

---
clicks: 3
---

# One position, four representations

<NotationMorph :clicks="$clicks" />

<!--
TIMING: 2 minutes.
SAY: Same board, same move, four encodings. FEN stores the position, UCI names the move for machines, SAN names it for people, PGN stores the whole game. The workshop consumes exactly these and no others.
CLICK: 3. FEN is visible first; each click steps to UCI, SAN, PGN while the board and the highlighted move stay fixed.
SOURCE: the position is the Ruy Lopez after 2...Nc6; the move is 3. Bb5 in every representation.
CUT: never; every dataset slide depends on these names.
FALLBACK: static board and text, no dependencies.
-->

---
clicks: 2
---

# Stockfish has one job here

<div class="stockfish-lines">
  <div class="sf-line">The model proposes.</div>
  <div v-click="1" class="reserve sf-line">python-chess validates.</div>
  <div v-click="2" class="reserve sf-line">Stockfish evaluates.</div>
</div>

<p class="statement-quiet">
Stockfish is not the fine-tuned model and not the dataset. It is an optional
oracle for move quality, centipawn loss, and tactical checks. python-chess
handles legal state transitions without pretending to evaluate strategy.
</p>

<style>
.stockfish-lines {
  margin-top: 1.2rem;
}
.sf-line {
  font-size: 1.7rem;
  font-weight: 700;
  padding: 0.45rem 0;
}
</style>

<!--
TIMING: 60 seconds.
SAY: Three different jobs, three different owners. Keeping them separate is what makes the evals honest.
CLICK: 2. Validate, then evaluate.
SOURCE: none.
CUT: never.
FALLBACK: static.
-->

---

# The room, live

<LiveRoom />

<p class="join-line">
Open the board URL on the screen. Enter your name. Your workspace is yours;
everyone else's is read-only.
</p>

<style>
.join-line {
  max-width: 40rem;
  margin: 1rem auto 0;
  font-size: 0.9rem;
  color: var(--ink-soft);
  text-align: center;
}
</style>

<!--
TIMING: 2 minutes, budget 90 seconds of dead air while the room joins.
SAY: Say the board URL out loud, twice. Every match, every clock, every sample; this panel calls the same API the workspaces use.
CLICK: none; the panel is live data, not staged reveals.
SOURCE: GET /presenter/games through the deck's /api proxy, polled every 3 seconds. LIVE chip when connected.
CUT: never on the default route; this is the handoff to the whiteboard.
FALLBACK: backend down shows a terse offline hint; a mid-talk drop keeps the last numbers visible with a reconnecting note.
-->
