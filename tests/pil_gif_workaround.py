from PIL import Image


im = Image.open("img\mosaicTexture.gif")

print(im.mode)

im.seek(2)

im = im.convert('RGBA')
im.palette = None
im = im.resize((320, 240), Image.LANCZOS)
im = im.convert('P')
im.save("output.png")
