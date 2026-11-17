# Signature extraction mechanics

Colour keys the separation. Pen ink measured blueness (`B - max(R,G)`) 27-33;
printed black, box rules and grey stamps sit at or below 11. Alpha from
`clip((blue - 4) / (hi - 4))` gated by a despeckled `blue > 20` mask dilated 2 px:
the antialiased ring survives, the blue cast on printed grey becomes nothing.
Black-ink signatures have no chroma and fall back to darkness — give those a
crop that excludes body text, because geometry alone cannot separate them.

Alpha compositing on white paper is unforgiving of two mistakes:

- **Un-blend the paper out of every pixel** before saving:
  `restored = (px - paper_rgb * (1 - a)) / max(a, 0.08)`. Without it the
  antialiased edge keeps paper colour and composites as a pale halo. `paper_rgb`
  is the per-channel 90th percentile of the crop.
- **Clamp the faint rim to the ink colour.** The `/max(a, 0.08)` floor overshoots to
  white exactly where a is smallest, and that rim is what notches a dark rule the tail
  crosses. Take the mean of `px[alpha > 0.9]` and assign it to every pixel with
  `alpha < 0.6`; they are too faint to read anyway, and their colour stops being
  paper-white.
- **Never Gaussian-blur the alpha.** On 1-2 px strokes a 0.6 px blur drops almost
  every pixel below full alpha and the result reads washed out. Cut at `scale=4` and
  resample the RGBA down to the placement size with LANCZOS instead: the alpha ramp has
  pixels to spend, the peak survives, the stair-steps smooth. `scale=2` is the floor,
  not the target — under-upscaled output is the "increase the quality" complaint.

Geometry traps, all of which looked plausible and were wrong:

- Dilating "by shifting the accumulator" compounds to `n(n+1)/2` px — a 44 px
  horizontal spread becomes ~990 px and merges the whole page into one blob. Always
  shift the ORIGINAL mask into a copy.
- Despeckle at `>= 1` orthogonal neighbour, not `>= 2`. Two eats thin stroke ends
  and clips the tail at scan resolution.
- Stray filters must key on VERTICAL overlap with the main stroke band. Keeping
  only blobs wider than the main one throws away every letter but the first.
- Decide chroma per crop, not per page. On a text page the signature is ~0.03% of
  dark pixels, so a page-level test concludes "no blue" and the printed lines win
  the ranking. Penalise candidate blobs with `blue_frac < 0.02` when the page holds
  >1500 blue pixels at all.
- Auto-detect rankings can be trusted only on a clear margin. If the top two
  scores are close, pass an explicit roi.
