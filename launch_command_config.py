import argparse


def GetArguments():
    defaultSettings = {
        "inputImagePath": "img/inputTexture.gif",
        "tileImagePath": "img/mosaicTexture.gif",
        "outputImagePath": "output.gif",
        "animationOffsetImagePath": None,
        "tileResolution": 25,
        "inputImageFramerate": None,
        "tileImageFramerate": None,
        "maxFramerateStretch": 0.1,
        "maxRepetitions": 10,
        "tileAnimationOffsetStrength": 1,
    }

    parser = argparse.ArgumentParser(
        description="Amogus Twerk Mosaic Gif Generator")

    parser.add_argument("-i", "--inputImagePath",
                        help="Input Image (Gif) for the animation",
                        default=defaultSettings["inputImagePath"])

    parser.add_argument("-t", "--tileImagePath",
                        help="Image (Gif) for the tiles",
                        default=defaultSettings["tileImagePath"])

    parser.add_argument("-o", "--outputImagePath",
                        help="Output image",
                        default=defaultSettings["outputImagePath"])

    parser.add_argument("-ao", "--animationOffsetImagePath",
                        help="Offset image for tiles",
                        default=defaultSettings["animationOffsetImagePath"])

    parser.add_argument("-r", "--tileResolution",
                        help="Amount of mosaic tiles in width", type=int,
                        default=defaultSettings["tileResolution"])

    parser.add_argument("-if", "--inputImageFramerate",
                        help="Framerate of the input Image (don't set for automatic dectection)", type=int,
                        default=defaultSettings["inputImageFramerate"])

    parser.add_argument("-tf", "--tileImageFramerate",
                        help="Framerate of the tile Image (don't set for automatic dectection)", type=int,
                        default=defaultSettings["tileImageFramerate"])

    parser.add_argument("-s", "--maxFramerateStretch",
                        help="Maximum framerate stretch (in %%)", type=int,
                        default=defaultSettings["maxFramerateStretch"])

    parser.add_argument("-re", "--maxRepetitions",
                        help="Maximum loops", type=int,
                        default=defaultSettings["maxRepetitions"])

    parser.add_argument("-os", "--tileAnimationOffsetStrength",
                        help="Strength of the animation offset", type=int,
                        default=defaultSettings["tileAnimationOffsetStrength"])

    args = parser.parse_args()

    return args
