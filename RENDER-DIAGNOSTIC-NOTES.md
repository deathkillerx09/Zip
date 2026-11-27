> Historical note: superseded by README.md (v2.1). See the Test report for what was verified in this build.

# Temporary AI Money Town visual diagnostics

The world diagnostics show 362 scene groups and active draw calls, but the owner still sees a blue viewport. This build adds a read-only mesh/material/frustum audit and an optional magenta camera-centred render probe.

After launching, open Chrome DevTools Console and run:

```js
window.__AMT_TOWN_VISUAL_AUDIT()
```

Then run:

```js
window.__AMT_TOWN_SHOW_RENDER_PROBE()
```

A large magenta cube should appear in the centre of the view. If it appears, WebGL is drawing and the fault is in the world objects, transforms, materials, or visibility. If it does not appear, the fault is in canvas presentation/renderer state. Remove it with:

```js
window.__AMT_TOWN_REMOVE_RENDER_PROBE()
```

This is a diagnostic build; no database data or business logic was changed.
