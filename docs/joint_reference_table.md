# Joint reference table (auto-generated)

**DO NOT EDIT BY HAND.** Regenerate with:
```
..\.venv-emg2pose310\Scripts\python.exe inference\make_joint_reference.py
```

- `N_joint` = **20**, units = **radians**
- Ordering: `emg2pose/constants.py::JOINTS` (official)
- Limits: `generic_hand_model.json::joint_limits[0:20]` (generic model, NOT applied as a clamp)
- Sign: `+` = flexion for FE joints (verified by FK, 15/15); AA is per-finger

| # | name | finger | group | DOF | motion | + means | min (deg) | max (deg) | range (deg) | min (rad) | max (rad) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | `THUMB_CMC_FE` | thumb | proximal | FE | flexion/extension | flexion | -45.11 | +73.75 | 118.86 | -0.7873 | +1.2873 |
| 1 | `THUMB_CMC_AA` | thumb | proximal | AA | abduction/adduction | per-finger (no global sign) -- see docs/joint_angle_definition.md 3.2 | -35.05 | +35.05 | 70.11 | -0.6118 | +0.6118 |
| 2 | `THUMB_MCP_FE` | thumb | mid | FE | flexion/extension | flexion | +0.00 | +73.75 | 73.75 | +0.0000 | +1.2873 |
| 3 | `THUMB_IP_FE` | thumb | distal | FE | flexion/extension | flexion | -14.81 | +62.30 | 77.11 | -0.2585 | +1.0873 |
| 4 | `INDEX_MCP_AA` | index | proximal | AA | abduction/adduction | per-finger (no global sign) -- see docs/joint_angle_definition.md 3.2 | -19.32 | +27.92 | 47.24 | -0.3373 | +0.4873 |
| 5 | `INDEX_MCP_FE` | index | proximal | FE | flexion/extension | flexion | -16.46 | +76.62 | 93.08 | -0.2873 | +1.3373 |
| 6 | `INDEX_PIP_FE` | index | mid | FE | flexion/extension | flexion | +0.00 | +107.86 | 107.86 | +0.0000 | +1.8825 |
| 7 | `INDEX_DIP_FE` | index | distal | FE | flexion/extension | flexion | +0.00 | +82.14 | 82.14 | +0.0000 | +1.4337 |
| 8 | `MIDDLE_MCP_AA` | middle | proximal | AA | abduction/adduction | per-finger (no global sign) -- see docs/joint_angle_definition.md 3.2 | -27.92 | +16.46 | 44.38 | -0.4873 | +0.2873 |
| 9 | `MIDDLE_MCP_FE` | middle | proximal | FE | flexion/extension | flexion | -16.46 | +82.35 | 98.81 | -0.2873 | +1.4373 |
| 10 | `MIDDLE_PIP_FE` | middle | mid | FE | flexion/extension | flexion | +0.00 | +107.86 | 107.86 | +0.0000 | +1.8825 |
| 11 | `MIDDLE_DIP_FE` | middle | distal | FE | flexion/extension | flexion | +0.00 | +82.14 | 82.14 | +0.0000 | +1.4337 |
| 12 | `RING_MCP_AA` | ring | proximal | AA | abduction/adduction | per-finger (no global sign) -- see docs/joint_angle_definition.md 3.2 | -16.46 | +16.46 | 32.92 | -0.2873 | +0.2873 |
| 13 | `RING_MCP_FE` | ring | proximal | FE | flexion/extension | flexion | -16.46 | +88.08 | 104.54 | -0.2873 | +1.5373 |
| 14 | `RING_PIP_FE` | ring | mid | FE | flexion/extension | flexion | +0.00 | +107.86 | 107.86 | +0.0000 | +1.8825 |
| 15 | `RING_DIP_FE` | ring | distal | FE | flexion/extension | flexion | +0.00 | +82.14 | 82.14 | +0.0000 | +1.4337 |
| 16 | `PINKY_MCP_AA` | pinky | proximal | AA | abduction/adduction | per-finger (no global sign) -- see docs/joint_angle_definition.md 3.2 | -39.38 | +27.92 | 67.30 | -0.6873 | +0.4873 |
| 17 | `PINKY_MCP_FE` | pinky | proximal | FE | flexion/extension | flexion | -27.92 | +93.81 | 121.73 | -0.4873 | +1.6373 |
| 18 | `PINKY_PIP_FE` | pinky | mid | FE | flexion/extension | flexion | +0.00 | +107.86 | 107.86 | +0.0000 | +1.8825 |
| 19 | `PINKY_DIP_FE` | pinky | distal | FE | flexion/extension | flexion | +0.00 | +82.14 | 82.14 | +0.0000 | +1.4337 |

