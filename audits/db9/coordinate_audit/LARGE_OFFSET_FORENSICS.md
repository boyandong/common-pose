# LARGE-OFFSET FORENSICS

Frozen plan: `c59fe01370d48aedeed56ef7a4103506d14a298edb794723be3720531edd62c6`

Focus dimensions flagged by the distributional branch: `middle_dip_flexion`, `ring_dip_flexion`, `pinky_mcp_flexion`.

## 1. The decisive test — DB9 channel behaviour between documented anchors

Movement 11 (documented extended reference) and movement 8 (adduction of extended fingers) bracket the extended end; movements 6 (fist) and 1 (thumb-up, long fingers held flexed) bracket the flexed end. A correctly calibrated channel must move POSITIVELY towards flexion.

| DB9 channel | extended anchor | flexed anchor | signed change | DB1 / DB2 / DB5 |
|---|---|---|---|---|
| `MCP2_f` | +8.71 | +43.12 | **+34.41** | +15.3 / +43.2 / +22.5 |
| `PIP2` | +7.88 | +93.95 | **+86.07** | +24.7 / +98.5 / +21.8 |
| `DIP2` | +0.34 | +23.79 | **+23.45** | +8.2 / +33.3 / -5.4 |
| `MCP3_f` | +6.08 | +89.74 | **+83.66** | +15.1 / +93.6 / +5.8 |
| `PIP3` | +0.08 | -4.25 | **-4.33** | -4.4 / -3.7 / -7.1 |
| `DIP3` | -4.31 | -26.24 | **-21.93** | -3.4 / -22.4 / -10.4 |
| `MCP4_f` | +5.76 | +75.26 | **+69.50** | -0.8 / +76.5 / +1.2 |
| `PIP4` | +0.51 | +15.34 | **+14.83** | -9.2 / +54.3 / -8.5 |
| `DIP4` | -1.67 | -18.70 | **-17.04** | -2.8 / -14.7 / -16.5 |
| `MCP5_f` | +8.75 | +114.98 | **+106.23** | -2.6 / +116.0 / -17.9 |
| `PIP5` | +2.56 | +27.18 | **+24.61** | +6.5 / +36.5 / +1.6 |
| `DIP5` | -2.24 | -14.53 | **-12.29** | -8.8 / -7.9 / -12.6 |

## 2. Same question inside DB9 source subsets

| dimension | DB1 median | DB2 median | DB5 median | DB2−DB1 |
|---|---|---|---|---|
| `index_mcp_flexion` | +19.65 | +4.11 | +16.42 | **-15.54** |
| `index_pip_flexion` | +28.79 | -0.84 | +29.30 | **-29.64** |
| `index_dip_flexion` | +1.85 | +1.41 | +0.92 | **-0.44** |
| `middle_mcp_flexion` | +40.44 | +0.36 | +44.39 | **-40.08** |
| `middle_pip_flexion` | +1.67 | +0.53 | +0.47 | **-1.14** |
| `middle_dip_flexion` | -21.25 | -9.36 | -35.36 | **+11.88** |
| `ring_mcp_flexion` | +16.11 | +2.47 | +47.88 | **-13.64** |
| `ring_pip_flexion` | +2.16 | +2.91 | +2.38 | **+0.76** |
| `ring_dip_flexion` | -29.67 | -6.02 | -29.25 | **+23.65** |
| `pinky_mcp_flexion` | +56.22 | +4.19 | +54.12 | **-52.04** |
| `pinky_pip_flexion` | +7.54 | +3.16 | +6.08 | **-4.38** |
| `pinky_dip_flexion` | -11.38 | -4.31 | -16.89 | **+7.07** |

## 3. Complement relationships and offset constancy

| dimension | DB9 q05..q95 | emg2pose q05..q95 | diff range | constant? | QQ slope | π-complement distance |
|---|---|---|---|---|---|---|
| `index_mcp_flexion` | -20.5..+69.4 | -16.0..+64.2 | 9.8 | True | 0.89 | 150.6 |
| `index_pip_flexion` | -16.6..+118.2 | -5.0..+112.9 | 27.0 | False | 0.83 | 148.8 |
| `index_dip_flexion` | -21.6..+83.0 | -5.0..+54.4 | 45.2 | False | 0.80 | 167.6 |
| `middle_mcp_flexion` | -11.5..+111.6 | -19.0..+74.2 | 44.7 | False | 0.74 | 146.0 |
| `middle_pip_flexion` | -30.2..+50.9 | -2.2..+99.2 | 43.5 | False | 4.07 | 139.7 |
| `middle_dip_flexion` | -122.7..+24.7 | +1.7..+87.0 | 89.3 | False | 0.52 | 178.5 |
| `ring_mcp_flexion` | -9.5..+99.7 | -21.3..+72.5 | 32.3 | False | 0.99 | 146.7 |
| `ring_pip_flexion` | -49.8..+108.6 | -5.0..+101.1 | 59.4 | False | 1.91 | 134.5 |
| `ring_dip_flexion` | -189.2..+37.3 | -4.8..+78.3 | 157.6 | False | 0.40 | 183.0 |
| `pinky_mcp_flexion` | -15.0..+145.4 | -29.9..+75.5 | 65.1 | False | 0.56 | 121.7 |
| `pinky_pip_flexion` | -6.6..+75.2 | +0.9..+98.1 | 15.4 | False | 1.39 | 148.0 |
| `pinky_dip_flexion` | -64.4..+18.6 | -5.0..+81.1 | 47.3 | False | 1.00 | 183.9 |

## 4. Wrapping

| dimension | span | > 1 turn | \|x\|>180 | min | max |
|---|---|---|---|---|---|
| `index_mcp_flexion` | 173.4 | False | 0 | -71.6 | 101.8 |
| `index_pip_flexion` | 211.8 | False | 0 | -60.4 | 151.3 |
| `index_dip_flexion` | 311.6 | False | 22 | -103.3 | 208.3 |
| `middle_mcp_flexion` | 210.7 | False | 0 | -61.9 | 148.8 |
| `middle_pip_flexion` | 223.6 | False | 0 | -106.5 | 117.1 |
| `middle_dip_flexion` | 356.4 | False | 38 | -268.2 | 88.2 |
| `ring_mcp_flexion` | 201.3 | False | 0 | -63.1 | 138.2 |
| `ring_pip_flexion` | 452.5 | True | 52 | -155.6 | 296.9 |
| `ring_dip_flexion` | 453.8 | True | 696 | -324.6 | 129.2 |
| `pinky_mcp_flexion` | 262.7 | False | 3 | -78.3 | 184.4 |
| `pinky_pip_flexion` | 227.1 | False | 0 | -77.1 | 150.0 |
| `pinky_dip_flexion` | 194.6 | False | 0 | -141.2 | 53.4 |

## 5. Between-subject stability inside DB9

| dimension | median of subject medians | IQR | p5..p95 | subjects < −90° |
|---|---|---|---|---|
| `index_mcp_flexion` | +6.98 | 15.15 | -3.9..+35.6 | 0/77 |
| `index_pip_flexion` | +0.65 | 34.74 | -8.3..+51.2 | 0/77 |
| `index_dip_flexion` | +1.42 | 6.38 | -8.8..+14.0 | 0/77 |
| `middle_mcp_flexion` | +2.08 | 36.98 | -5.1..+59.0 | 0/77 |
| `middle_pip_flexion` | +0.81 | 5.64 | -12.3..+11.0 | 0/77 |
| `middle_dip_flexion` | -14.79 | 18.06 | -38.2..+1.6 | 0/77 |
| `ring_mcp_flexion` | +3.18 | 12.63 | -2.1..+50.0 | 0/77 |
| `ring_pip_flexion` | +4.58 | 11.77 | -25.9..+19.8 | 0/77 |
| `ring_dip_flexion` | -14.08 | 21.33 | -48.7..+18.0 | 0/77 |
| `pinky_mcp_flexion` | +5.64 | 37.13 | -2.7..+74.2 | 0/77 |
| `pinky_pip_flexion` | +3.92 | 4.56 | -0.5..+24.0 | 0/77 |
| `pinky_dip_flexion` | -7.24 | 13.22 | -24.1..+8.3 | 0/77 |

## 6. Raw sensor behaviour and implied calibration

| channel | implied slope | slope +fraction | glove change (ext→fist) | angle change | signs agree |
|---|---|---|---|---|---|
| `DIP2` | +0.345 | 0.97 | +71.5 | +19.4 | True |
| `DIP3` | -0.649 | 0.12 | +14.1 | -14.6 | False |
| `DIP4` | +8.167 | 1.00 | -0.4 | -1.6 | True |
| `DIP5` | -0.058 | 0.35 | -2.2 | -3.3 | True |
| `PIP2` | +1.401 | 0.94 | +7.9 | +87.2 | True |
| `PIP3` | +0.084 | 0.57 | +107.0 | -5.6 | False |
| `PIP4` | +0.268 | 0.70 | +31.8 | +13.7 | True |
| `PIP5` | +0.306 | 0.95 | +21.1 | +20.5 | True |
| `MCP2_f` | +0.995 | 1.00 | +29.6 | +29.4 | True |
| `MCP3_f` | +0.922 | 0.99 | +32.1 | +83.4 | True |
| `MCP4_f` | +0.391 | 0.58 | -4.6 | +66.5 | False |
| `MCP5_f` | +0.995 | 0.81 | +5.3 | +103.9 | True |

## 7. Candidate transforms (frozen T0–T7)

| dimension | T0 W1 | best | W1 after | reduction | residual |
|---|---|---|---|---|---|
| `index_mcp_flexion` | 3.81 | T7_affine | 2.41 | 0.369 | -3.63 |
| `index_pip_flexion` | 9.72 | T7_affine | 5.01 | 0.485 | -12.79 |
| `index_dip_flexion` | 12.00 | T7_affine | 2.94 | 0.755 | -2.82 |
| `middle_mcp_flexion` | 12.71 | T7_affine | 9.28 | 0.270 | -20.87 |
| `middle_pip_flexion` | 38.57 | T7_affine | 14.13 | 0.634 | -2.51 |
| `middle_dip_flexion` | 58.08 | T1_negate | 16.54 | 0.715 | -1.54 |
| `ring_mcp_flexion` | 7.96 | T0_identity | 7.96 | 0.000 | -5.10 |
| `ring_pip_flexion` | 35.99 | T7_affine | 15.21 | 0.577 | -13.08 |
| `ring_dip_flexion` | 61.31 | T7_affine | 29.89 | 0.512 | +40.45 |
| `pinky_mcp_flexion` | 30.20 | T7_affine | 8.04 | 0.734 | -10.45 |
| `pinky_pip_flexion` | 18.00 | T7_affine | 7.37 | 0.590 | -12.09 |
| `pinky_dip_flexion` | 29.07 | T1_negate | 4.87 | 0.833 | +3.94 |

> A transform is NOT accepted because Wasserstein falls. The decisive evidence against all transforms is section 1: the DB9 DIP channels fail an internal, transform-free, cross-dataset-free test.

