<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/feder-cr/AIHawk/main/assets/aihawk-logo-dark.png">
  <img alt="AIHawk" src="https://raw.githubusercontent.com/feder-cr/AIHawk/main/assets/aihawk-logo-light.png" width="380">
</picture>

**AIHawk is an open-source AI browser agent: a web browsing agent with a real browser. You say what you want in plain language, and it browses, clicks, types and reads the actual web to get it done.**

<sub>FEATURED IN</sub><br>
[**Business Insider**](https://www.businessinsider.com/aihawk-applies-jobs-for-you-linkedin-risks-inaccuracies-mistakes-2024-11) ·
[**TechCrunch**](https://techcrunch.com/2024/10/10/a-reporter-used-ai-to-apply-to-2843-jobs/) ·
[**Semafor**](https://www.semafor.com/article/09/12/2024/linkedins-have-nots-and-have-bots) ·
[**Wired**](https://www.wired.it/article/aihawk-come-automatizzare-ricerca-lavoro/) ·
[**The Verge**](https://www.theverge.com/2024/10/10/24266898/ai-is-enabling-job-seekers-to-think-like-spammers) ·
[**Vanity Fair**](https://www.vanityfair.it/article/intelligenza-artificiale-candidature-di-lavoro) ·
[**404 Media**](https://www.404media.co/i-applied-to-2-843-roles-the-rise-of-ai-powered-job-application-bots/)

</div>

---

## Two ways to use this browser agent

### 1. From your assistant, over MCP

```bash
pip install aihawk
invisible-playwright fetch
```

Then tell your assistant it exists.

**Claude Code:**

```bash
claude mcp add --scope user stealth -- invisible-playwright-mcp
```

**Codex:**

```bash
codex mcp add stealth -- invisible-playwright-mcp
```

**Gemini CLI:**

```bash
gemini mcp add --scope user stealth invisible-playwright-mcp
```

### 2. Standalone: the web UI

We bring the interface, you bring an [OpenRouter](https://openrouter.ai) key.
Chat on the left, the live browser on the right.

```bash
pip install aihawk
invisible-playwright fetch
aihawk ui --openrouter-key sk-or-...
```

Then open **http://127.0.0.1:8765** and type the same thing.

---

## What to ask a web browsing agent

Anything that needs real web automation: a browser rather than an API, and a
person's judgement about what is on the page.

> Go to `<paste the URL>`. One way, Milan to Lisbon, economy, one checked bag,
> one adult. Check every date from the 12th to the 16th of next month, one at a
> time, and read the cheapest fare for each day. The date field is a calendar
> widget, so click the days rather than typing them. If a date has no
> availability, say so. Do not guess a number.

It drives the page the way a person would: the pointer moves, keys are pressed,
and it refuses to set a form field from JavaScript even when that would be
quicker, because a page can tell the difference.

## Options: proxy, profile, seed

- **`--openrouter-key`** Your key, or the `OPENROUTER_API_KEY` variable.
- **`--model`** An OpenRouter model id, or `AIHAWK_MODEL`. Defaults to `z-ai/glm-4.6`.
- **`--proxy`** Optional. `http://user:pass@proxy.example.com:8080` or
  `socks5://proxy.example.com:1080`. Host and port are both required. The
  timezone, locale and egress follow it.
- **`--binary`** An engine binary you already have. It must be the build the seal
  pins, or startup refuses: this skips the download, not the version check.
- **`--seed`** An integer. Same seed, same browser identity, every run.
- **`--profile-dir`** A directory to keep the profile in, so logins and cookies
  survive restarts.
- **`--headed`** Show the browser window. The interface shows you the page anyway.
- **`--host`, `--port`** `127.0.0.1` and `8765`. Changing the host
  exposes an interface that has no authentication.

### A `.env` beside the command

Rather than retyping the key and the binary path, put them in a `.env` in the
directory you run from:

```
OPENROUTER_API_KEY=sk-or-...
STEALTHFOX_BINARY=/path/to/firefox
```

It is read at startup, and on the way in it **never overrides** something
already set, so the order is `--flag` > the environment > `.env` > the default.
Only the directory you are in is read - there is no search upwards, so running
from a subfolder cannot silently pick up a different key. The startup line names
the variables it applied and never prints their values.

Passing `--openrouter-key` puts the key in your shell history, and on Linux in
the process list. `OPENROUTER_API_KEY` in the environment or in a `.env` avoids
both.

## The wiki: AI browser-agent guides

The reading room around the agent lives in the
[wiki](https://github.com/feder-cr/AIHawk/wiki): the
[AI browser-agent landscape: browser-use, Operator-style and
computer-use agents compared](https://github.com/feder-cr/AIHawk/wiki/guides-alternatives-and-comparisons),
[what to check when an agent gets blocked](https://github.com/feder-cr/AIHawk/wiki/why-does-my-ai-agent-get-blocked),
and [what happened to OpenAI Operator](https://github.com/feder-cr/AIHawk/wiki/is-openai-operator-still-available),
among others. Worked examples, transcripts and their outputs live in
[articles/](https://github.com/feder-cr/AIHawk/tree/main/articles).

## The rest of the family: browser MCP server, engine, core

- **[invisible-playwright-mcp](https://github.com/feder-cr/invisible-playwright-mcp)**
  The MCP server from option 1. Tools only, no interface.
- **[invisible_playwright](https://github.com/feder-cr/invisible_playwright)**
  The engine, as a Python library, for writing code instead of prompts. The API
  is Playwright's.
- **[invisible_core](https://github.com/feder-cr/invisible_core)**
  Seed to fingerprint to preferences, proxy and geolocation.

## Using it responsibly

This automates a browser under your control. Read the terms of the sites you
point it at, respect their rate limits, and do not submit anything a human has
not read.

## License

[MIT](https://github.com/feder-cr/AIHawk/blob/main/LICENSE). Everything
distributed before 2 September 2026 was released under AGPL-3.0 and stays under
it.


## 🌐 Web Resources & Interactive Index
- [CATEGORY ANIMAL216](https://studyplayings.pages.dev/category-animal216.html)
- [CUBES 2048IO](https://quizverses.github.io/cubes-2048io.html)
- [CAR DEALER IDLE](https://iskillquest.pages.dev/car-dealer-idle.html)
- [MAHJONG CONNECT TILES](https://quizverses.github.io/mahjong-connect-tiles.html)
- [CATEGORY BRAIN261](https://studyplaying.github.io/category-brain261.html)
- [ASMR BEAUTY HOMELESS](https://quizverses.github.io/asmr-beauty-homeless.html)
- [OFFROAD LIFE 3D](https://themindplay.pages.dev/offroad-life-3d.html)
- [CATEGORY CASUAL 6](https://learnquester.pages.dev/category-casual-6.html)
- [BATTLE SIMULATOR SANDBOX](https://studyplayings.web.app/battle-simulator-sandbox.html)
- [GELATINO](https://themindplay.pages.dev/gelatino.html)
- [CATEGORY TRAFFIC34](https://iskillquest.pages.dev/category-traffic34.html)
- [THE PRISM CITY DETECTIVES](https://studyplayings.web.app/the-prism-city-detectives.html)
- [MINDBLOW](https://quizverses.github.io/mindblow.html)
- [NEKOS ADVENTURE](https://studyplayings.web.app/nekos-adventure.html)
- [SAILOR CHIC VS PIRATE CHARM](https://studyplayings.web.app/sailor-chic-vs-pirate-charm.html)
- [TONY ARCHER](https://theskillquest.pages.dev/tony-archer.html)
- [CATEGORY UNBLOCKED GAMES](https://quizverses.pages.dev/category-unblocked-games.html)
- [SLIPPERY DRIFT RACING](https://studyplayings.web.app/slippery-drift-racing.html)
- [FOOD TRUCK CHEF COOKING](https://studyquests.github.io/food-truck-chef-cooking.html)
- [CATEGORY INTERSTELLARNETWORK](https://studyquests.github.io/category-interstellarnetwork.html)
- [SLITHERCRAFT IO](https://studyplayings.web.app/slithercraft-io.html)
- [FASHION BATTLE FOR SURVIVAL](https://themindplay.pages.dev/fashion-battle-for-survival.html)
- [DINO IDLE PARK](https://themindplay.pages.dev/dino-idle-park.html)
- [CATEGORY FLASH 2](https://themindplays.pages.dev/category-flash-2.html)
- [IDLE PET](https://themindplay.github.io/idle-pet.html)
- [8 BALL POOL BILLIARDS MULTIPLAYER](https://studyplayings.web.app/8-ball-pool-billiards-multiplayer.html)
- [BUBBLE SHOOTER ULTIMATE](https://themindplay.pages.dev/bubble-shooter-ultimate.html)
- [CATEGORY MAKEUP51](https://skillplay.github.io/category-makeup51.html)
- [SIEGE BREAK](https://themindplay.pages.dev/siege-break.html)
- [CARS VS ZOMBIES](https://studyquesthub.web.app/cars-vs-zombies.html)
- [COFFEE CRAZE SORTING GAME](https://studyplayings.web.app/coffee-craze-sorting-game.html)
- [INDEX4](https://themindplays.pages.dev/index4.html)
- [MERGE BRAINROT 2](https://themindplaying.web.app/merge-brainrot-2.html)
- [CATEGORY ADVENTURE 2](https://quizverses.pages.dev/category-adventure-2.html)
- [OBBY TSUNAMI ESCAPE 1 BY CAR](https://quizverses.github.io/obby-tsunami-escape-1-by-car.html)
- [CRAZY PLANE LANDING](https://themindplay.pages.dev/crazy-plane-landing.html)
- [CATEGORY COOKING](https://studyquesthub.web.app/category-cooking.html)
- [2 PLAYER MINI CHALLENGE](https://themindplays.pages.dev/2-player-mini-challenge.html)
- [CATEGORY FLASH](https://thelearnquester.web.app/category-flash.html)
- [INDEX21](https://studyquesthub.web.app/index21.html)
- [GEOMETRY VIBES 3D](https://themindplay.pages.dev/geometry-vibes-3d.html)
- [SLIDE RABBIT](https://studyquests.github.io/slide-rabbit.html)
- [BLUE GIRLS MAKEUP](https://themindskillplayplay.pages.dev/blue-girls-makeup.html)
- [CATEGORY SIMULATION 2](https://iskillquest.pages.dev/category-simulation-2.html)
- [OFFLINE FPS ROYALE](https://themindplay.pages.dev/offline-fps-royale.html)
- [CATEGORY BATTLE524](https://studyplaying.github.io/category-battle524.html)
- [HALLOWEEN CHALLENGE](https://studyplayings.web.app/halloween-challenge.html)
- [DRAWING SQUARES](https://skillplay.github.io/drawing-squares.html)
- [RUSSIAN DERBY CRASH](https://themindplay.github.io/russian-derby-crash.html)
- [GEOMETRY VIBES X BALL](https://studyplayings.web.app/geometry-vibes-x-ball.html)
- [2048 BLOCKS DESTRUCTION](https://themindplays.pages.dev/2048-blocks-destruction.html)
- [WORMSARENAIO](https://studyquests.github.io/wormsarenaio.html)
- [BOXING GANG STARS](https://quizverses.github.io/boxing-gang-stars.html)
- [ELLIE AND FRIENDS VENICE CARNIVAL](https://studyplayings.pages.dev/ellie-and-friends-venice-carnival.html)
- [RIDE SHOOTER](https://learnquester.github.io/ride-shooter.html)
- [SAUSAGE FLIP FREE](https://themindplays.pages.dev/sausage-flip-free.html)
- [RAGDOLL BOB PUZZLE](https://studyplayings.pages.dev/ragdoll-bob-puzzle.html)
- [TRY TO COUNT THE BOXES BRAIN TRAINING](https://themindplay.github.io/try-to-count-the-boxes-brain-training.html)
- [CATEGORY BATTLE ROYALE25](https://skillplay.github.io/category-battle-royale25.html)
- [LAZY WORKERS](https://studyplaying.github.io/lazy-workers.html)
- [CHRISTMAS CANDY ESCAPE 3D](https://studyquests.github.io/christmas-candy-escape-3d.html)
- [SIGIL SEEKER](https://quizverses.github.io/sigil-seeker.html)
- [ANIMALON EPIC MONSTERS BATTLE](https://themindplaying.web.app/animalon-epic-monsters-battle.html)
- [TILE FRUITS](https://themindplay.pages.dev/tile-fruits.html)
- [TANGRAM PUZZLE](https://theskillquest.pages.dev/tangram-puzzle.html)
- [BRAINROTS LAVA SURVIVE ONLINE](https://studyplayings.web.app/brainrots-lava-survive-online.html)
- [GALACTIC CRUSADE CLICKER](https://quizverses.github.io/galactic-crusade-clicker.html)
- [CRAZY TUNNEL](https://quizverses.github.io/crazy-tunnel.html)
- [SUM MASTER](https://skillplay.github.io/sum-master.html)
- [CAPYBARA MUKBANG ASMR](https://themindskillplayplay.pages.dev/capybara-mukbang-asmr.html)
- [RUNIC BLOCK COLLAPSE](https://themindplay.pages.dev/runic-block-collapse.html)
- [MERGE TOWER HERO](https://themindplay.pages.dev/merge-tower-hero.html)
- [SURVIVE LAVA FOR BRAINROTS](https://iskillplay.web.app/survive-lava-for-brainrots.html)
- [OCEAN POP](https://themindplay.pages.dev/ocean-pop.html)
- [ARCHERY RAGDOLL](https://themindplaying.web.app/archery-ragdoll.html)
- [CUTE CATS ADVENTURES](https://themindplay.pages.dev/cute-cats-adventures.html)
- [KING OF THE HILL](https://quizverses.github.io/king-of-the-hill.html)
- [DOODLE DINO RUN](https://studyplayings.web.app/doodle-dino-run.html)
- [CAR ESCAPE](https://quizverses.github.io/car-escape.html)
- [CATEGORY AIRPLANE](https://studyplaying.github.io/category-airplane.html)
- [CANDY MONSTER RAFFI](https://theskillquest.pages.dev/candy-monster-raffi.html)
- [CATEGORY BASKETBALL](https://themindskillplayplay.pages.dev/category-basketball.html)
- [STICKMAN ARCHER SHOOTING ARROWS AT REDS](https://themindplay.pages.dev/stickman-archer-shooting-arrows-at-reds.html)
- [GLOVES OF BLOCK](https://iskillquest.pages.dev/gloves-of-block.html)
- [CATEGORY THINKY](https://learnquester.github.io/category-thinky.html)
- [3D ACRYLIC NAIL NAIL ART GAME](https://quizverses-9d2f2.web.app/3d-acrylic-nail-nail-art-game.html)
- [MEOW MARKET](https://skillplay.github.io/meow-market.html)
- [ADDICTION SOLITAIRE](https://learnquester.github.io/addiction-solitaire.html)
- [MR BOUNCE](https://themindplay.github.io/mr-bounce.html)
- [CRASH THE ROBOT](https://studyplayings.web.app/crash-the-robot.html)
- [CATEGORY CASUAL 8](https://iskillplay.web.app/category-casual-8.html)
- [CATEGORY AGILITY 2](https://themindskillplayplay.pages.dev/category-agility-2.html)
- [LOGIC STORM ANIMALS PUZZLE](https://themindplays.pages.dev/logic-storm-animals-puzzle.html)
- [MAGICAL DIARY PAPER DRESS UP](https://theskillquest.pages.dev/magical-diary-paper-dress-up.html)
- [SNAKE MASTERS](https://theskillquest.pages.dev/snake-masters.html)
- [CATEGORY TOWER DEFENSE 2](https://iskillquest.pages.dev/category-tower-defense-2.html)
- [IDLE BARBER SHOP](https://iskillquest.pages.dev/idle-barber-shop.html)
- [WORD JAM ASSOCIATION PUZZLE](https://themindplay.github.io/word-jam-association-puzzle.html)
- [TAPKO](https://studyplayings.web.app/tapko.html)
- [CYBERPUNK CITY HAIRSTYLES](https://themindplays.pages.dev/cyberpunk-city-hairstyles.html)
- [PARTY ANIMALS CATS EVOLUTION](https://themindplay.github.io/party-animals-cats-evolution.html)
- [DIG OUT OF PRISON](https://studyplayings.pages.dev/dig-out-of-prison.html)
- [CATEGORY SOLITAIRE](https://studyplayings.web.app/category-solitaire.html)
- [CATEGORY ANIMAL](https://themindskillplayplay.pages.dev/category-animal.html)
- [GRANNY PILLS DEFEND CACTUSES](https://themindplay.pages.dev/granny-pills-defend-cactuses.html)
- [HIGH HEELS COLLECT RUN](https://learnquester.github.io/high-heels-collect-run.html)
- [SPIN SPIN](https://themindplay.github.io/spin-spin.html)
- [CATEGORY SANDBOX](https://learnquester.github.io/category-sandbox.html)
- [RICH CHOICE RUN](https://quizverses.github.io/rich-choice-run.html)
- [DINOSAUR RAMPAGE](https://skillplay.github.io/dinosaur-rampage.html)
- [INDEX35](https://themindskillplayplay.pages.dev/index35.html)
- [CATEGORY BATTLE CATEGORY](https://themindzone.pages.dev/category-battle-category.html)
- [HARVESTING VEGGIES](https://studyplayings.pages.dev/harvesting-veggies.html)
- [BLUE GIRLS MAKEUP](https://quizverses.pages.dev/blue-girls-makeup.html)
- [CATEGORY CAN T STOP PLAYING212](https://learnquester.github.io/category-can-t-stop-playing212.html)
- [TENTRIX](https://thequizzone.pages.dev/tentrix.html)
- [INDEX3](https://learnquester.github.io/index3.html)
- [SCREW JAM FUN PUZZLE GAME](https://studyquests.pages.dev/screw-jam-fun-puzzle-game.html)
- [MR LONG LEGS](https://studyquesthub.web.app/mr-long-legs.html)
- [OFFROAD CLIMB 4X4](https://themindplaying.web.app/offroad-climb-4x4.html)
- [SUDOKU GURU CLASSIC SUDOKU](https://themindplay.pages.dev/sudoku-guru-classic-sudoku.html)
- [SNEAKY FRIENDS](https://themindskillplayplay.pages.dev/sneaky-friends.html)
- [CLEAN THE FLOOR](https://quizverses.pages.dev/clean-the-floor.html)
- [GUMMY MERGE](https://learnquester.github.io/gummy-merge.html)
- [BELL MADNESS](https://studyplayings.web.app/bell-madness.html)
- [CATEGORY BIKE 3](https://iskillplay.web.app/category-bike-3.html)
- [LABUBU MERGE CLICKER](https://iskillquest.pages.dev/labubu-merge-clicker.html)
- [Z STICK DUEL FIGHTING](https://studyplayings.pages.dev/z-stick-duel-fighting.html)
- [SPRUNKI QUIZ](https://themindzone.pages.dev/sprunki-quiz.html)
- [CATEGORY TANK](https://studyplayings.web.app/category-tank.html)
