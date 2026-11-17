# Full EIDOLON WGSL Raymarching Shader

This is a complete, production-grade SDF raymarcher in WGSL for wgpu. It implements the full hybrid organic/geometric architecture described in the skill.

## Structure

The shader contains:

1. **Fullscreen triangle vertex shader** (`vs_fullscreen`) — 3 vertices covering the entire viewport
2. **SDF Primitives** — sdSphere, sdBox, sdCapsule, sdTorus, sdOctahedron
3. **SDF Operations** — opUnion, opSmoothUnion, opSubtraction, opRepLim
4. **3D Noise** — hash31, noise3, fbm3 (5-octave fractal Brownian motion)
5. **Organic Forms** — organicTentacle (12-segment capsule chain with sine wave + taper + tip bulb), organicBlob (5 smin-blended spheres with surface noise), organicScene (3 tentacles + central blob)
6. **Geometric Forms** — geometricMandelbox (8-iteration Mandelbox with box+sphere fold), geometricCrystal (folded octahedra with recursive subdivision), geometricFoldedSpace (infinite grid folding), geometricScene (Mandelbox + crystals + folded grid)
7. **Hybrid Scene SDF** — sceneSDF blends organic and geometric via `mix(organic, geometric, morph)`
8. **Raymarcher** — 128-step loop with early termination, normal estimation via central differences
9. **Lighting** — diffuse, ambient occlusion, rim light, onset flash, surface noise detail
10. **Camera** — orbiting camera with audio-reactive radius and height
11. **Fragment shader** — `fs_sdf` driving the entire pipeline

## Key Constants

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Max raymarch steps | 128 | Depth complexity |
| Max distance | 20.0 | Far plane |
| Surface epsilon | 0.001 | Hit threshold |
| Normal epsilon | 0.001 | For central diff gradient |
| AO range | 0.1 | Ambient occlusion probe distance |
| FBM octaves | 5 | Organic surface noise detail |

## Morph Factor Mapping

| Morph | Visual State | Audio Driver |
|-------|-------------|--------------|
| 0.0 - 0.3 | Pure organic: tentacles, bioluminescent blue/violet | Low energy, low onset |
| 0.3 - 0.6 | Hybrid: tentacles crystallizing, forms mixed | Moderate energy |
| 0.6 - 0.8 | Mostly geometric: Mandelbox dominates | High energy + onset |
| 0.8 - 1.0 | Pure geometric: ice crystals, folded space | Peak energy + treble |

## File Location

The complete shader is at:
`/home/kubuntux/Documents/EIDOLON/apps/eidolon-renderer/src/organism.wgsl`

And the Rust renderer that drives it:
`/home/kubuntux/Documents/EIDOLON/apps/eidolon-renderer/src/renderer.rs`
