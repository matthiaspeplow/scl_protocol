"""
Image conversion module for SCL uploader.
Converts BMP, GIF, and PNG monochrome images to XMP format and back.
"""

import tempfile
import struct
from pathlib import Path
from typing import Optional, Tuple

from .exceptions import ImageConversionError

try:
    from PIL import Image
except ImportError:
    Image = None

# PIL Image mode constants for better readability
# Reference: https://pillow.readthedocs.io/en/stable/handbook/concepts.html#modes
MODE_GRAYSCALE = 'L'      # 8-bit grayscale (0=black, 255=white)
MODE_PALETTE = 'P'         # 8-bit pixels using a color palette
MODE_MONOCHROME = '1'      # 1-bit black and white (no grayscale)


def is_convertible_image(filename: str) -> bool:
    """
    Check if a file is a convertible image format.
    
    Args:
        filename: Path or filename to check
    
    Returns:
        True if file extension is BMP, GIF, or PNG
    """
    ext = Path(filename).suffix.lower()
    return ext in ['.bmp', '.gif', '.png']


def convert_to_xmp(image_path: str, output_path: Optional[str] = None, xmp_type: int = 1) -> Tuple[str, bool]:
    """
    Convert a monochrome or grayscale image (BMP, GIF, PNG) to XMP format.
    
    XMP Format:
    
    Type 1 (4-color grayscale):
    - File header (10 bytes):
      * XMPType (1 byte): Type 1 for grayscale
      * PictureCount (1 byte): Number of images (usually 1)
      * Height (2 bytes, WORD, little-endian)
      * Width (2 bytes, WORD, little-endian)
      * Height repeated (2 bytes, WORD, little-endian)
      * Width repeated (2 bytes, WORD, little-endian)
    - Image data:
      * 2 bits per pixel (4 grayscale levels with INVERTED polarity: 0=lit/white, 3=dark/black)
      * Pixels stored row-first, then column (down each column from top to bottom)
      * Each byte stores 4 pixels vertically (2 bits each, from LOW bits to HIGH bits)
      * Bit mapping: Row A in d1,d0; Row B in d3,d2; Row C in d5,d4; Row D in d7,d6
      * Total bytes needed: 10 + (H+3)/4 * W
    
    Type 2 (single-color monochrome):
    - File header (6 bytes):
      * XMPType (1 byte): Type 2 for single-color
      * PictureCount (1 byte): Number of images (usually 1)
      * Height (2 bytes, WORD, little-endian)
      * Width (2 bytes, WORD, little-endian)
    - Image data:
      * 1 bit per pixel
      * Pixels stored row-first, then column
      * Each byte stores 8 pixels vertically (from high bit to low bit)
      * Total bytes needed: (H+7)/8 * W
    
    Args:
        image_path: Path to source image file
        output_path: Optional destination path for XMP file.
                    If None, creates a temporary file.
        xmp_type: XMP format type (1 for 4-color grayscale, 2 for monochrome).
                 Default is 1 (grayscale) for better compatibility.
    
    Returns:
        Tuple of (output_path, is_temporary)
        - output_path: Path to the converted XMP file
        - is_temporary: True if a temporary file was created
    
    Raises:
        ImageConversionError: If conversion fails or PIL is not available
    """
    if Image is None:
        raise ImageConversionError(
            "Pillow (PIL) is required for image conversion. "
            "Install it with: pip install Pillow"
        )
    
    # Validate XMP type
    if xmp_type not in [1, 2]:
        raise ImageConversionError(
            f"Invalid XMP type: {xmp_type}. Must be 1 (grayscale) or 2 (monochrome)."
        )
    
    # Validate input file
    input_path = Path(image_path)
    if not input_path.exists():
        raise ImageConversionError(f"Image file not found: {image_path}")
    
    # Check if it's a supported format
    if not is_convertible_image(str(input_path)):
        raise ImageConversionError(
            f"Unsupported image format: {input_path.suffix}. "
            "Only BMP, GIF, and PNG are supported."
        )
    
    try:
        # Load image
        img = Image.open(input_path)
        
        # Convert based on XMP type
        if xmp_type == 1:
            # Type 1: 4-color grayscale (2 bits per pixel)
            # Need grayscale image - convert color/RGB images to grayscale
            if img.mode not in [MODE_GRAYSCALE, MODE_PALETTE]:
                img = img.convert(MODE_GRAYSCALE)
            # Also convert palette images to proper grayscale
            if img.mode == MODE_PALETTE:
                img = img.convert(MODE_GRAYSCALE)
        else:
            # Type 2: Monochrome (1 bit per pixel)
            # Need pure black and white image
            if img.mode != MODE_MONOCHROME:
                # Convert color/RGB images to grayscale first
                if img.mode not in [MODE_GRAYSCALE, MODE_MONOCHROME]:
                    img = img.convert(MODE_GRAYSCALE)
                # Then convert grayscale to pure black/white using dithering
                img = img.convert(MODE_MONOCHROME)
        
        width, height = img.size
        
        # Determine output path
        is_temp = False
        if output_path is None:
            # Create temporary file with .xmp extension (lowercase for temp files)
            fd, output_path = tempfile.mkstemp(suffix='.xmp', prefix='scl_upload_')
            # Close the file descriptor as we'll write to it ourselves
            import os
            os.close(fd)
            is_temp = True
        else:
            output_path = str(output_path)
            # Ensure .XMP extension (uppercase to match controller convention)
            if not output_path.lower().endswith('.xmp'):
                output_path += '.XMP'
        
        # Build XMP file
        with open(output_path, 'wb') as f:
            if xmp_type == 1:
                # Type 1: 4-color grayscale format
                picture_count = 1
                
                # Pack header: 10 bytes only (controller format)
                # Byte 0: XMP Type (1)
                # Byte 1: Picture count (1)
                # Bytes 2-3: Height (WORD)
                # Bytes 4-5: Width (WORD)
                # Bytes 6-7: Height repeated (WORD)
                # Bytes 8-9: Width repeated (WORD)
                # Note: Controller does NOT write 16 reserved bytes - data starts at byte 10
                header = struct.pack('<BBHHHH', 
                                   1,              # XMP Type 1
                                   picture_count,  # Picture count
                                   height,         # Height
                                   width,          # Width  
                                   height,         # Height repeated
                                   width)          # Width repeated
                f.write(header)
                # No reserved bytes - data starts immediately
                
                # Convert image data: 2 bits per pixel, 4 pixels per byte (vertical)
                # Per spec: "row first, then column" - process each column going down rows
                # Bytes needed per column: (height + 3) // 4
                bytes_per_column = (height + 3) // 4
                
                # Process column by column (left to right)
                for x in range(width):
                    # Process this column in chunks of 4 rows (2 bits each)
                    for byte_row in range(bytes_per_column):
                        byte_value = 0
                        # Pack 4 rows into one byte (2 bits each, from LOW bits to HIGH bits)
                        # Per spec: Row A in d1,d0; Row B in d3,d2; Row C in d5,d4; Row D in d7,d6
                        for pixel_pos in range(4):
                            y = byte_row * 4 + pixel_pos
                            if y < height:
                                # Get grayscale pixel value (0-255)
                                pixel = img.getpixel((x, y))
                                # Map 0-255 to 0-3 (2 bits) with INVERTED polarity
                                # Controller uses: 0=lit/white, 3=dark/black (inverted from standard)
                                # PIL: 0=black, 255=white, so we invert: 255->0, 0->3
                                gray_level = 3 - min(3, pixel // 64)
                                # Position in byte: Row A (pixel 0) at bits 1,0; Row B at bits 3,2, etc.
                                shift = pixel_pos * 2
                                byte_value |= (gray_level << shift)
                        
                        f.write(bytes([byte_value]))
            
            else:
                # Type 2: Single-color monochrome format
                picture_count = 1
                
                # Pack header: BYTE, BYTE, WORD, WORD (little-endian)
                header = struct.pack('<BBHH', 2, picture_count, height, width)
                f.write(header)
                
                # Convert image data to XMP format
                # Format: 1 bit per pixel, 8 pixels per byte (vertical)
                # Bytes needed per column: (height + 7) // 8
                bytes_per_column = (height + 7) // 8
                
                # Process column by column (left to right)
                for x in range(width):
                    # Process this column in chunks of 8 rows
                    for byte_row in range(bytes_per_column):
                        byte_value = 0
                        # Pack 8 rows into one byte (from d7 to d0)
                        for bit_pos in range(8):
                            y = byte_row * 8 + bit_pos
                            if y < height:
                                # Get pixel value (0 or 255 for '1' mode images)
                                pixel = img.getpixel((x, y))
                                # XMP format: 1 = lit/white, 0 = dark/black
                                # PIL '1' mode: 0 = black, 255 = white
                                if pixel:  # White pixel
                                    byte_value |= (1 << (7 - bit_pos))
                        
                        f.write(bytes([byte_value]))
        
        return output_path, is_temp
        
    except Exception as e:
        # Clean up temporary file if created
        if output_path and is_temp:
            try:
                Path(output_path).unlink(missing_ok=True)
            except:
                pass
        
        raise ImageConversionError(f"Failed to convert image to XMP: {e}")


def convert_from_xmp(xmp_path: str, output_path: str) -> bool:
    """
    Convert an XMP format file to another image format (BMP, GIF, PNG).
    The output format is determined by the output_path extension.
    
    Args:
        xmp_path: Path to source XMP file
        output_path: Destination path with desired extension (.bmp, .gif, .png)
    
    Returns:
        True if conversion successful
    
    Raises:
        ImageConversionError: If conversion fails or PIL is not available
    """
    if Image is None:
        raise ImageConversionError(
            "Pillow (PIL) is required for image conversion. "
            "Install it with: pip install Pillow"
        )
    
    # Validate input file
    input_path = Path(xmp_path)
    if not input_path.exists():
        raise ImageConversionError(f"XMP file not found: {xmp_path}")
    
    # Validate output format
    output_ext = Path(output_path).suffix.lower()
    if output_ext not in ['.bmp', '.gif', '.png']:
        raise ImageConversionError(
            f"Unsupported output format: {output_ext}. "
            "Only BMP, GIF, and PNG are supported."
        )
    
    try:
        # Read XMP file
        with open(xmp_path, 'rb') as f:
            data = f.read()
        
        if len(data) < 6:
            raise ImageConversionError("XMP file too small")
        
        # Parse header
        xmp_type = data[0]
        picture_count = data[1]
        
        if xmp_type == 1:
            # Type 1: 4-color grayscale format
            if len(data) < 10:
                raise ImageConversionError("Invalid Type 1 XMP file header")
            
            height = struct.unpack('<H', data[2:4])[0]
            width = struct.unpack('<H', data[4:6])[0]
            
            # Image data starts at byte 10
            image_data = data[10:]
            
            # Create grayscale image
            img = Image.new('L', (width, height))
            pixels = img.load()
            
            # Decode: 2 bits per pixel, 4 pixels per byte (vertical)
            bytes_per_column = (height + 3) // 4
            
            # Process column by column
            for x in range(width):
                for byte_row in range(bytes_per_column):
                    byte_offset = x * bytes_per_column + byte_row
                    if byte_offset >= len(image_data):
                        break
                    
                    byte_value = image_data[byte_offset]
                    
                    # Extract 4 pixels from this byte (2 bits each)
                    for pixel_pos in range(4):
                        y = byte_row * 4 + pixel_pos
                        if y < height:
                            # Extract 2-bit gray level
                            shift = pixel_pos * 2
                            gray_level = (byte_value >> shift) & 0x03
                            
                            # Convert from inverted polarity (0=white, 3=black) to standard (0=black, 255=white)
                            pixel_value = (3 - gray_level) * 85  # Map 0-3 to 255-0 in steps of 85
                            pixels[x, y] = pixel_value
            
        elif xmp_type == 2:
            # Type 2: Single-color monochrome format
            height = struct.unpack('<H', data[2:4])[0]
            width = struct.unpack('<H', data[4:6])[0]
            
            # Image data starts at byte 6
            image_data = data[6:]
            
            # Create monochrome image
            img = Image.new('1', (width, height))
            pixels = img.load()
            
            # Decode: 1 bit per pixel, 8 pixels per byte (vertical)
            bytes_per_column = (height + 7) // 8
            
            # Process column by column
            for x in range(width):
                for byte_row in range(bytes_per_column):
                    byte_offset = x * bytes_per_column + byte_row
                    if byte_offset >= len(image_data):
                        break
                    
                    byte_value = image_data[byte_offset]
                    
                    # Extract 8 pixels from this byte (1 bit each)
                    for bit_pos in range(8):
                        y = byte_row * 8 + bit_pos
                        if y < height:
                            # Extract bit (1=white, 0=black)
                            bit_value = (byte_value >> (7 - bit_pos)) & 0x01
                            pixels[x, y] = 255 if bit_value else 0
        
        else:
            raise ImageConversionError(f"Unsupported XMP type: {xmp_type}")
        
        # Save to output format
        img.save(output_path)
        return True
        
    except Exception as e:
        raise ImageConversionError(f"Failed to convert XMP to image: {e}")


def needs_conversion(filename: str) -> bool:
    """
    Check if a file needs conversion before upload.
    
    Args:
        filename: Path or filename to check
    
    Returns:
        True if file should be converted to XMP before upload
    """
    return is_convertible_image(filename)
