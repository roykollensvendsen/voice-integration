# Where you are, while you move

*A proposal, waiting for Roy's yes or no. Nothing here is built yet.*

## What it is for

Roy asked for this on 2026-10-10, for driving and walking:

1. **Hermes knows where you are, all the time.** Today the page asks for the
   position once, when a call opens. Only the bridge holds it, and Hermes never
   gets it.
2. **Hermes knows which way you are going.** That lets you ask "what is that on
   the left?" as you pass something.
3. **A guided tour.** Hermes says something about a place as you reach it,
   without being asked.
4. **The route is followed, and shown on a map in the app** when you ask for
   it.

## What I propose

**The phone sends position, direction and speed every few seconds, while a call
is open.** The app does this itself, with Android's location service, because
a page in a locked phone is paused. The bridge keeps the latest reading. When
no call is open, nothing is sent, unless you have switched on "follow the
route".

**Hermes is told where you are with every turn.** One line goes with each
question to Hermes: for example, "Roy is on Fv 410 at Skuggevik, heading north
at 60 km/h, at 14:02". Nothing else changes for Hermes. A session you talk to
is not told unless it asks.

**"What is on the left?" is answered by the bridge.** It knows where you are and
which way you are facing. It asks OpenStreetMap what is there, within a few
hundred metres on that side. It answers in a sentence, and Hermes can tell you
more. The same goes for right, ahead and behind.

**A tour is a list of places, each with a few words to say.** Hermes can make
one when you ask ("make a tour of the coast road to Arendal"), or you can give
it one. As you come within a set distance of a place, the voice says its words.
That happens only during a call. Waking the phone for a tour stop is a later
step.

**The route is kept, and shown on a map when you ask.** "Vis kartet" or "show
me the route" opens a map on the page, with your route and where you are now.
The map uses OpenStreetMap's tiles.

## What changes, and what it costs

- **A rule changes.** Today a position is held in memory, written nowhere, and
  forgotten on restart. To follow a route, it has to be written down. I propose
  it is kept on the laptop only, for 30 days, and that you can wipe it by voice
  ("slett ruta").
- **Who learns where you are.** Hermes's model, Claude Haiku via OpenRouter,
  would see your position with every turn you send it. OpenStreetMap would see
  which map tiles are fetched and which places are looked up. Neither gets the
  whole route.
- **Battery.** GPS every few seconds while you drive costs some battery. That is
  usually fine in a car on charge.
- **Money.** The position costs nothing. Talking about it costs the same voice
  minutes as any other call.

## In steps

1. The app sends position, direction and speed during a call. Hermes is told,
   and "what is on the left" works.
2. The route is kept on the laptop and shown on a map when you ask.
3. Guided tours.

Each step can be tried in the car before the next one starts.

## What Roy decides

- Whether the route may be written down on the laptop at all, and for how long.
- Whether Hermes's model may see the position with every turn, or only when you
  ask about where you are.
- Whether the map may fetch its tiles from OpenStreetMap.
