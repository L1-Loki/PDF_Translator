"""
Convert Loki.png to Loki.ico for PyInstaller
"""
from PIL import Image

# Đọc ảnh PNG
img = Image.open('assets/Loki.png')

# Convert sang RGBA nếu cần
if img.mode != 'RGBA':
    img = img.convert('RGBA')

# Resize về các kích thước chuẩn cho icon
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save('assets/Loki.ico', format='ICO', sizes=icon_sizes)

print("✓ Đã tạo Loki.ico từ Loki.png")
