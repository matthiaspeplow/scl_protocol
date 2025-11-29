# XMP Format Technical Specification

## Overview

XMP is a proprietary bitmap format used by LyTech LED controllers. The scl_protocol library supports both XMP format types and automatically converts BMP, GIF, and PNG images to XMP format during upload.

## XMP Format Types

### Type 1: 4-Color Grayscale (Default, Recommended)

**File Structure:**

- **Header: 26 bytes**

  - Byte 0: XMP Type (0x01)
  - Byte 1: Picture Count (usually 0x01)
  - Bytes 2-3: Height (WORD, little-endian)
  - Bytes 4-5: Width (WORD, little-endian)
  - Bytes 6-7: Height repeated (WORD, little-endian)
  - Bytes 8-9: Width repeated (WORD, little-endian)
  - Bytes 10-25: Reserved (16 bytes of zeros)
- **Image Data:**

  - **2 bits per pixel** (4 grayscale levels)
    - 0 = black
    - 1 = dark gray
    - 2 = light gray
    - 3 = white
  - **Storage:** Column-first (left to right)
  - **Packing:** Each byte stores 4 pixels vertically (2 bits each, from high bits to low bits)
  - **Total bytes:** Header (26) + (Height+3)/4 × Width

**Example:** 40×1168 pixel image = 26 + 10×1168 = 11,706 bytes

**Why Type 1 is Default:**

- Best controller compatibility
- Matches native controller format
- Supports grayscale images without dithering

### Type 2: Single-Color Monochrome

**File Structure:**

- **Header: 6 bytes**

  - Byte 0: XMP Type (0x02)
  - Byte 1: Picture Count (usually 0x01)
  - Bytes 2-3: Height (WORD, little-endian)
  - Bytes 4-5: Width (WORD, little-endian)
- **Image Data:**

  - **1 bit per pixel** (monochrome)
    - 0 = black
    - 1 = white
  - **Storage:** Column-first (left to right)
  - **Packing:** Each byte stores 8 pixels vertically (from bit 7 to bit 0)
  - **Total bytes:** Header (6) + (Height+7)/8 × Width

**Example:** 40×1168 pixel image = 6 + 5×1168 = 5,846 bytes (50% smaller than Type 1)

**When to Use Type 2:**

- Simple black and white displays
- File size is a concern
- No need for grayscale levels

## Implementation Details

### Pixel Storage Order

Both formats store pixels column-first (left to right), with multiple pixels packed vertically into each byte:

**Type 1 (2 bits/pixel):**

```
Byte = [pixel0_hi, pixel0_lo, pixel1_hi, pixel1_lo, pixel2_hi, pixel2_lo, pixel3_hi, pixel3_lo]
       [  bit 7  ,   bit 6  ,   bit 5  ,   bit 4  ,   bit 3  ,   bit 2  ,   bit 1  ,   bit 0  ]
```

**Type 2 (1 bit/pixel):**

```
Byte = [pixel0, pixel1, pixel2, pixel3, pixel4, pixel5, pixel6, pixel7]
       [ bit 7,  bit 6,  bit 5,  bit 4,  bit 3,  bit 2,  bit 1,  bit 0]
```

### Grayscale Mapping (Type 1)

The converter maps 8-bit grayscale values (0-255) to 2-bit levels:

- 0-63 → 0 (black)
- 64-127 → 1 (dark gray)
- 128-191 → 2 (light gray)
- 192-255 → 3 (white)

## Usage

### Default (Type 1 - Grayscale)

```python
from scl_protocol import convert_to_xmp

# Convert to Type 1 (4-color grayscale)
output_path, is_temp = convert_to_xmp('input.png', 'output.xmp')
# or explicitly:
output_path, is_temp = convert_to_xmp('input.png', 'output.xmp', xmp_type=1)
```

### Type 2 (Monochrome)

```python
from scl_protocol import convert_to_xmp

# Convert to Type 2 (monochrome)
output_path, is_temp = convert_to_xmp('input.png', 'output.xmp', xmp_type=2)
```

## Compatibility

### Type 1 vs Type 2 Choice

- **Type 1 (Default)**: Better controller compatibility, matches native format
- **Type 2**: Smaller file size (50% of Type 1), suitable for simple monochrome displays

### Controller Behavior

When downloading XMP files from the controller:

- Controllers typically store Type 1 format
- Filenames are uppercased (DOS convention): `PICTURE.XMP`
- Downloaded Type 1 files should match locally converted Type 1 files byte-for-byte (except minor header variations)

## History

### Version 0.1.0

- Initial implementation with Type 2 (monochrome) only
- File size mismatch with controller-downloaded files

### Version 0.2.0

- Added Type 1 (4-color grayscale) support
- Made Type 1 the default for better compatibility
- Updated documentation and interactive test script
- File sizes now match controller's native format
