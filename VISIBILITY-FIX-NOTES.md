> Historical note: superseded by README.md (v2.1). The town now runs the isometric renderer by default and the Three.js scene is opt-in.

# AI MONEY TOWN — Interior Camera and World-Return Fix

This update addresses the blue-only viewport and the diagnostic that reported `worldVisible: false`.

## Root cause identified from the browser diagnostic

- The diagnostic showed `worldVisible: false`, which is the state set intentionally when the player enters a building.
- The old interior camera code still used the outdoor camera's 24-unit look-ahead and spawned the player at `z=6.3` near the room wall.
- As a result, the camera could sit outside the interior room and aim through a wall, showing only the blue scene background even though the interior objects existed.
- The Central Bank can open a modal dialog, and its modal can intercept the first Escape key. This made keyboard-only exiting unclear.

## What changed

- Interior player spawn moved to the centre of the room.
- Interior camera now uses a short look-ahead and is clamped inside the room bounds.
- Returning outside restores the outdoor camera distance and pitch.
- Added a visible **Return to town** button while inside a building.
- Added a second **Return to town** button inside the town interaction dialog, including the Central Bank dialog.
- Added `window.__AMT_TOWN_RETURN_OUTSIDE()` as an emergency browser-console recovery command.
- Expanded `window.__AMT_TOWN_DIAGNOSTICS()` to report the active building, interior object count, and scene visibility.
- Added a defensive visibility watchdog that restores the outside groups when no interior is active.
- Cache-busted the bootstrap and 3D module URLs to avoid loading an older cached bundle.

## How to use the recovery control

- If inside a building, click **Return to town**.
- If a modal is open, use the **Return to town** button inside the modal.
- Emergency browser-console command: `window.__AMT_TOWN_RETURN_OUTSIDE()`.
- The diagnostics command is: `window.__AMT_TOWN_DIAGNOSTICS()`.

## Validation

- Backend and frontend tests: 29 passed.
- `node --check` passed for the city bundle, bootstrap, and dashboard JavaScript.
- Python compile check passed for backend and tests.
- The source and served bundle both contain the interior-camera correction.
- Actual WebGL rendering on the user's Windows/Chrome device must still be visually confirmed; automated headless checks cannot prove the final pixels on Intel Iris Xe hardware.

## Database

The database from the source ZIP is included and was not modified during this update. Back it up before replacing an existing working folder.
