from PIL import Image

mask = Image.open("img/mosaicTexture.gif")
mask.seek(2)
mask = mask.copy()

mask.show()
mask = mask.convert(mode="RGBA")
layers = mask.split()

for layer in layers:
    layer.show()

pass
