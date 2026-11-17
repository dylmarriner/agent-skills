---
name: audio-reactive-sdf
description: Build audio-reactive SDF raymarching visualizers with wgpu + WGSL. Full pipeline from audio capture (PipeWire) through DSP analysis to real-time signed-distance-field rendering, including organic/geometric hybrid morphing.
allowed-tools: Terminal Grep Read
metadata:
  tags: audio-reactive, sdf, raymarching, wgpu, wgsl, generative-art
---

# Audio-Reactive SDF Raymarching

Build real-time audio-reactive visualizers where the entire scene is rendered via Signed Distance Field raymarching in a WGSL fragment shader, driven by audio analysis data.

## Architecture

```
Audio Source
    → PipeWire Capture (stream capture on default sink)
    → DSP Analysis (FFT, band energies, RMS, onset detection)
    → IPC (Unix socket, JSON serialized)
    → wgpu Renderer (Vulkan backend)
        → Uniform buffer (audio features + time + morph factor)
        → Fullscreen quad
        → Fragment shader: SDF raymarcher
            → Scene SDF (organic + geometric forms, blended by morph)
            → Normal estimation, lighting, ambient occlusion
```

## Key Patterns

### Audio Analysis
- Capture via PipeWire with `Direction::Input` and `StreamFlags::AUTOCONNECT`
- FFT size 2048 at 48kHz → ~21Hz frequency resolution
- 5 broad bands (sub 0-60Hz, bass 60-250Hz, low-mid 250-2000Hz, high-mid 2000-6000Hz, treble 6000Hz+)
- RMS for overall energy, spectral flux for onset detection

### SDF Raymarching in WGSL

**Primitives** (all return `f32` distance):
```
sdSphere(p, r)      → length(p) - r
sdBox(p, b)         → length(max(abs(p)-b, 0)) + min(max component, 0)
sdCapsule(p, a, b, r) → length(pa - ba*h) - r
sdTorus(p, t)       → length(vec2(length(p.xz)-t.x, p.y)) - t.y
sdOctahedron(p, s)  → (q.x+q.y+q.z-s) / sqrt(3)
```

**Operations**:
```
opUnion(d1, d2)           → min(d1, d2)
opSmoothUnion(d1, d2, k)  → mix(d2, d1, h) - k*h*(1-h)
opSubtraction(d1, d2)     → max(-d1, d2)
opRepLim(p, c, lim)       → p - c * clamp(round(p/c), -lim, lim)
```

**Raymarching loop**:
```wgsl
var t = 0.0;
for (var i = 0u; i < 128u; i++) {
    let p = ro + rd * t;
    let d = sceneSDF(p, time, morph);
    if d < 0.001 { hit = true; break; }
    if t > 20.0 { break; }
    t += d * 0.9;
}
```

**Normal estimation** (central differences):
```wgsl
let eps = 0.001;
let n = normalize(vec3(
    sceneSDF(pos + vec3(eps,0,0)) - sceneSDF(pos - vec3(eps,0,0)),
    sceneSDF(pos + vec3(0,eps,0)) - sceneSDF(pos - vec3(0,eps,0)),
    sceneSDF(pos + vec3(0,0,eps)) - sceneSDF(pos - vec3(0,0,eps)),
));
```

### Organic Forms (Tentacle Pattern)

A tentacle is a chain of capsules along a sine-modulated curve:
- N segments, each a `sdCapsule` between two animated points
- Sine wave displacement on X/Z axes, varying amplitude by segment (taper)
- Radius tapers from thick base to thin tip
- Segments blended with `opSmoothUnion` for organic continuity
- Optional pulsing bulb at tip driven by audio energy/bass

### Geometric Forms (Mandelbox Fractal)

```wgsl
for (i in 0..8) {
    z = abs(z) - 1.0;           // box fold
    let r2 = dot(z, z);         // sphere fold
    if r2 < minR2 { z *= fixR2/minR2; dz *= ...; }
    z = z * scale + p * 0.5;   // scale + translate
}
return length(z) / abs(dz) - 0.1;
```

### Hybrid Morph Bridge

The key architectural principle: **both organic and geometric forms are SDFs**, so they can be blended with a single `mix()` call:
```wgsl
fn sceneSDF(p, time, morph) -> f32 {
    let organic = organicScene(p, time);
    let geometric = geometricScene(p, time);
    return mix(organic, geometric, morph);
}
```

Where `morph` comes from audio analysis:
```rust
let morph = (energy * 0.6 + onset * 0.3 + treble * 0.1).clamp(0.0, 1.0);
```

## Critical WGSL Pitfalls

### Struct Alignment
The Rust `Uniforms` struct and the WGSL `Uniforms` struct must match **byte-for-byte**:
- **WGSL `mat4x4<f32>`** = 64 bytes (4×4 floats)
- **WGSL `f32`** = 4 bytes
- **WGSL `u32`** = 4 bytes
- **No implicit padding** at end of struct in WGSL

Do NOT add `_padding: [f32; 2]` or any trailing padding in the Rust struct unless the WGSL side has it. Use `bytemuck::{Pod, Zeroable}` on the Rust side and verify sizes match.

### Camera in the Shader
For a fullscreen quad renderer, compute camera rays entirely in the fragment shader:
```wgsl
// Camera orbit with audio reactivity
let cam_radius = 3.5 + bass * 0.3;
let cam_angle = time * 0.08 + energy * 0.5;
let ro = vec3(sin(cam_angle)*cam_radius, cam_height, cos(cam_angle)*cam_radius);
let rd = normalize(fwd + right*uv.x + up*uv.y);
```

### Noise Functions
Include hash-based 3D noise and FBM for organic surface detail:
```wgsl
fn hash31(p: vec3<f32>) -> f32 { fract(sin(dot(p, ...)) * 43758.5453) }
fn noise3(p: vec3<f32>) -> f32 { /* value noise */ }
fn fbm3(p: vec3<f32>) -> f32 { /* 5-octave fractal brownian motion */ }
```

## IPC Protocol

Communicate audio features from analysis process to renderer process:
- Unix domain socket at a known path (e.g., `/tmp/eidolon.sock`)
- JSON-encoded message containing: energy, sub/bass/mid/treble band levels, onset strength, behavior state, timestamps
- Renderer: connect, poll with 5s timeout (nonblocking + sleep loop)

See the [IPC crate pattern] for details — the renderer should handle disconnection gracefully by reconnecting on the next frame.

## References

- [Inigo Quilez SDF Tutorials](https://iquilezles.org/articles/)
- [Mandelbox Fractal](https://en.wikipedia.org/wiki/Mandelbox)
- [PipeWire API](https://docs.pipewire.org/)
- [wgpu WGSL Support](https://github.com/gfx-rs/wgpu)
