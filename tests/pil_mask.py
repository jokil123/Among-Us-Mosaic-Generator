from PIL import Image

mask = Image.open("cirnopyramid.gif")
mask.seek(2)
mask = mask.copy()
mask = mask.convert()

basecolor = Image.new("RGBA", (206, 184), color="red")

basecolor.putalpha(mask.convert("L"))

basecolor.show()
