Here is how I am thinking of the deck and the flow of things.

The plan below

My style is many slides high movements, many things happening on clicks and animations 
but very few words, Russel Davies style more or less.

Reference for splitting the deck into several sections in different files and 
iterate over each more efficiently, e.g. part 1, 2, and 3. https://sli.dev/features/importing-slides#importing-specific-slides


## Slide 1

This is the title slide

## Slide 2

Old picture of me from the when I first discovered chess

It can have "this is what I looked like when I discovered chess"

After a click, an image of the drawing of a book will appear and I will say 
"I bought a book and everything to get better at it, opened it 5 times and never saw it 
again, so I wasn't any good and didn't even keep playing after that"



## Slide 3 - Fast forward to april 2026

I have been using duolingo for years and although chess mode came out in June 2025

picture of the launch post

I didn't find out about until I was in Japan and went to open the app to practice a little bit of 
Japanese and then end up seeing it.

click: Picture of duo app on top of the previous one

click: picture of a game

click: picture of oscar

Oscar, the main player in the duo app, and I became best friends

click: picture of 5 games a day

click: picture 20 games a day

click: picture of a month later 500 games played in total

It is fair to say I got hooked. Even watched for the first time

click: queen's gambit picture

On my way back to Sydney from Japan, which, if you've done that flight or a similar one you know 
how lengthy it is, I notice that I wasn't able to play in Duo anymore

## Slide 4 - No internet

picture on the right of duo rendered useless given the lack of an internet connection

so I thought, I'm sure people have fine-tuned models on chess moves, but has anyone explained 
the process thoroughtly, release the models, and made something unique with these?

click: meme of dog thinking.

"what if I completely change what I had planned for my talk with less than a month to go"

click: meme of "what could possibly go wrong"

## Slide 5 - Video Recording Demo

This is sort of the end goal, a model I can run inside a TUI in termux and play against it as 
much as I want. It keeps track of games played including wins, losses, draws and so on. It let's me 
replay games to find mistakes, it is sassy a fuck, and it teaches me to get better, in particular 
how to win without barely taking any pieces from my opponent, because 

click: the art of war quote

## Slide 6 - But this is meant to be about all modalities, no?

Indeed, we can make 4 different models

The text based one is the game engine as we saw in the previous demo but what if it could 
relate each gamme to a real-world scenario

## Slide 7

example 1 of a final, check-mated board and the log of the game and the next to 
its the description

## Slide 8

example 2

## Slide 9

example 3

## Slide 10

The image one generates cool pieces and boards we could use as themes

click: image of a board and its pieces with a specific theme

click: another image with a different style of board and pieces

## Slide 11

The audio one generates sounds for when a piece defeats another, background 
music, white noise, or even text-to-speech we can use to call where to move to

click: audio example appears

click: another audio example appears


## Slide 12

The text description can generate different video examples

click: example 1

click: example 2


## Slide 13 - Question for the audience

Can you guess which examples were generated with a fine-tuned version and which weren't?

click: pictures of both text options
wait for answer, don't reveal yet

click: pictures of image examples
wait for answer, don't reveal yet

click: picture of audio examples
wait for answer, don't reveal yet

click: pictures of video examples
wait for answer, don't reveal yet

## Slide 14

Reveal answers in a table row by row

## Slide 15 - Why fine-tune?

Cost comparison table using available inference cost data for top models vs the required 
hardware to host equivalent, fine-tuned or not versions

1. Gemma fine-tuned running on your device vs inference on latest model by x provider
2. FLux Klein running on device or small rented gpu vs latest image model
3. MusicGen on device vs API provider like elevenlabs
4. LTX latest on rented hardware vs gemini omni cost

## Slide 16 - Why fine-tune? ctd.

Model providers don't have your proprietary data and while they

## Slide 17 - Why fine-tune? ctd.

Model providers don't know your style

click: goth-like minions

click: super jargon-heavy paragraph talking about the new lamps on employees's desks at the corporate office

click: bachata style background music, or maybe understanding slang (I can play a video here from 
thinking machines translating bad-mouthing a colleague in a joking way to corporate slang, brilliant)

click: example I worked on at canva were companies don't have our video templates to train on and 
fine-tuning a model allows us to endlessly customise them at a lower cost

## Slide 18 - Data is key

click: Circle with all the data we think is available in the internet

click: smaller circle with the data with think is accessible

click: overlapping circle with what we think is useful data of that

click: another separate circle with data we don't know exists


## Slide 19 - Cool bruh, what now?

gif of chunky boy deciding which cookie to eat

## Slide 20

You don't need to choose one and never look back, it is great to have options. The point I want 
to highlight is that a model provider will never know everything there is to know about you, 
your company and your world and it is great have the ability to mould intelligence to our will.

## Slide 21

a tree diagram on what models might look like in the future

but we're not there yet

## Slide 22

Enough preamble, let's get started

## Slide 23

Chess rules recap

## Slide 24

notations

click: show fen

click: show pgn

all others...

## Slide 25

A word on stockfish and other 

## Slide 26 - this slide and subsequent ones

Making a chess engine section and subsequent ones redisigned go from this one on

no bs at the end take the repo with you and so on, they know that already.

Black and white style similar to the polyglot presentation.

We need componenets to interact with in the presentation

afterwards we jump into the notebook

finish with the whiteboard
