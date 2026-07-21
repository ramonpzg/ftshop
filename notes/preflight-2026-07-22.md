# Workshop preflight: 22 July 2026

Run this list in order. Stop when the required path is solid. Optional model
and media paths do not get to delay the room.

## Required tonight

- [ ] Finish the default deck route and replace only the placeholders needed
  for that route.
- [ ] Convert `notebooks/full-session3.py` to the final Jupyter notebook, then
  restart the kernel and run the presenter path from top to bottom.
- [ ] From a clean checkout or temporary environment, run
  `just install --whiteboard`, `just install --deck`, and `just install --nb`.
- [ ] Start the room with `just start`. Start the deck and notebook separately
  with `just deck` and `just session-notebook`.
- [ ] Confirm the attendee list contains only `ramon`. The four
  `phase35-check` rows were removed directly after verifying that they owned no
  games, moves, dataset rows, attempts, scenarios, or evals.
- [ ] Use the presenter panel's page reset if the game state needs clearing.
  Do not run `just reset-db` immediately before the session: SQLite would lose
  the user identity while the preserved canvas kept its workspace shape.
- [ ] Confirm the Presentation tab is absent and the adaptation panel no longer
  overlaps the first workspace after the sync-room migration runs.
- [ ] Commit the final `data/canvas/snapshot.json` only after the room badge says
  `Canvas: saved` and the stack has stopped cleanly.
- [ ] Run `just test`, `just lint`, and `just typecheck` once on the final tree.

## Room network

- [ ] Put the presenter laptop and a phone on the actual workshop network.
  Run `just room-url` and open that URL on the phone.
- [ ] Verify join, board movement, attendee list, and reload from the phone.
  This catches venue Wi-Fi client isolation, which a localhost test cannot.
- [ ] Prefer a private travel router or hotspot if the venue network isolates
  clients or keeps expiring. The public captive portal is not part of the
  workshop architecture.
- [ ] Keep the laptop awake, connected to power, and exempt ports 5173, 3030,
  8000, 8010, and 8080 from the local firewall.
- [ ] Put the final `http://<LAN-IP>:5173` address somewhere visible after the
  network is known. Attendees need only port 5173; `/api` and `/sync` are
  same-origin proxies.

## Models and credentials

- [ ] Run `just download-models` once while the connection works. Do not include
  Stable Audio.
- [ ] Run `just start-gemma` and make one Chat Completions request against
  `http://127.0.0.1:8080/v1`.
- [ ] Keep `ROOM_MODEL_PLAY` unset unless `just load-test 40` against the real
  Gemma server prints a passing verdict. The default room path is free play;
  one presenter-led Gemma turn is enough.
- [ ] Test one Luna call, record its `x-request-id` on failure, and keep the
  narrowly bounded key-propagation retry available. Do not make attendee play
  depend on conference Internet.
- [ ] Confirm the API key and FAL key are in the uncommitted root `.env`, not in
  the deck, notebook output, shell history, or Git.

## Demo fallbacks

- [ ] Rehearse with the Internet disconnected. Deck, cached evidence, notebook,
  whiteboard drawing, and free play must still work.
- [ ] Rehearse with Gemma stopped. The board must label the model as unavailable
  or stay in the documented free-play path.
- [ ] Play the committed image, audio, and video evidence from disk. Check the
  projector output and room audio, not only laptop headphones.
- [ ] Keep MusicGen as the local audio path. Stable Audio and local Klein remain
  optional and do not belong in the timed run.
- [ ] Record the phone TUI demo and keep the recording local before relying on
  the live phone setup.

## Pack before leaving

- [ ] Laptop charger, phone charger, USB-C/HDMI adapters, clicker, and wired
  audio fallback.
- [ ] Local copies of the deck assets, TUI recording, model files, notebook,
  cached fixtures, and this repository.
- [ ] One screenshot or short recording for each outcome that depends on a
  provider.
