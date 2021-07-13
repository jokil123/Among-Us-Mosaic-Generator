from PIL import Image, ImageStat, ImageChops, ImageSequence
import math
import frame_align
import concurrent.futures
import launch_command_config


class Mosaic:
    tiles = [0, 0]
    tileSize = [0, 0]
    outputImageSize = [0, 0]
    pixelRatio = 1

    def __init__(self, tileDensity, inputImage, tileImage):
        self.tiles[0] = tileDensity
        self.tileImage = tileImage
        self.inputImage = inputImage

        self.CalculateDimensions()

    def CalculateDimensions(self):
        self.outputImageSize[0] = self.tileImage.width * self.tiles[0]
        self.pixelRatio = self.outputImageSize[0] / self.inputImage.width
        self.outputImageSize[1] = self.inputImage.height * self.pixelRatio
        self.tiles[1] = math.floor(
            self.outputImageSize[1] / self.tileImage.height)
        bottomMargin = self.outputImageSize[1] % self.tileImage.height
        verticalMargin = bottomMargin / self.tiles[1]

        self.tileSize[0] = self.tileImage.width
        self.tileSize[1] = math.floor(self.tileImage.height + verticalMargin)

        self.outputImageSize[1] = math.ceil(self.outputImageSize[1])

        self.tileTransforms = self.GetMosaicTileTransforms(
            self.tiles, self.tileSize)

    def InputImageCoord(self, position):
        return position / self.pixelRatio

    def InputImageCoords(self, positions):
        inputImageCoords = []
        for position in positions:
            inputImageCoords.append(self.InputImageCoord(position))

        return inputImageCoords

    def GetMosaicTileTransforms(self, tiles, tileSize):
        tileTransforms = []

        for xIndex in range(tiles[0]):
            for yIndex in range(tiles[1]):

                tileStartPosition = (xIndex * tileSize[0],
                                     yIndex * tileSize[1])

                tileEndPosition = (tileStartPosition[0] + tileSize[0],
                                   tileStartPosition[1] + tileSize[1])

                tileBoundingBox = tileStartPosition + tileEndPosition

                tilePosition = (xIndex, yIndex)

                tileTransforms.append({
                    "tilePosition": tilePosition,
                    "tileBoundingBox": tileBoundingBox
                })

        return tileTransforms


def CreateOffsetMosaic(mosaic, tileImageFrames, inputImage, animationOffsetStrength, animationOffset, tileImageAnimationOffsetTexture=None):
    tileImageFrameAmmount = len(tileImageFrames)

    outputImage = Image.new("RGBA", mosaic.outputImageSize)

    splits = []
    splitImages = []

    for i in range(mosaic.tiles[1]):
        start = i * mosaic.tiles[1]
        end = start + mosaic.tiles[1]

        splits.append(mosaic.tileTransforms[start:end])

    def CreateSplit(threadId):
        tileSplitImage = Image.new(
            "RGBA", (mosaic.tileSize[0], mosaic.outputImageSize[1]))

        for tile in splits[threadId]:
            tilePosition = tile["tilePosition"]
            tileBoundingBox = tile["tileBoundingBox"]

            if tileImageAnimationOffsetTexture == None:
                gradientFrameOffset = (
                    tilePosition[0] + (mosaic.tiles[1] - tilePosition[1])) % tileImageFrameAmmount

            else:
                gradientFrameOffset = (GetAveragePixelColor(
                    tileImageAnimationOffsetTexture.convert("LA"),
                    mosaic.InputImageCoords(tileBoundingBox)
                )[0] / 255) * tileImageFrameAmmount * animationOffsetStrength

            frame = round(gradientFrameOffset +
                          animationOffset) % tileImageFrameAmmount

            color = GetAveragePixelColor(
                inputImage, mosaic.InputImageCoords(tileBoundingBox),
            )

            solidColorTile = Image.new(
                "RGBA", tileBoundingBox[-2:], color=color)

            grayscaleTileImageTile = tileImageFrames[frame].convert(
                "LA").convert("RGBA")

            tile = ImageChops.multiply(
                solidColorTile, grayscaleTileImageTile)

            tile.putalpha(tileImageFrames[frame].split()[-1])

            tileSplitImage.paste(tile, (0, tileBoundingBox[1]))

        splitImages.append(
            {"image": tileSplitImage, "position": tileBoundingBox[0]})

    with concurrent.futures.ThreadPoolExecutor(max_workers=mosaic.tiles[0]) as executor:
        executor.map(CreateSplit, range(mosaic.tiles[0]))

    for splitImage in splitImages:

        outputImage.paste(splitImage["image"], (splitImage["position"], 0))

    return outputImage


def GetAveragePixelColor(img, box):
    cropArea = img.crop(box)
    imgStats = ImageStat.Stat(cropArea)
    averageColor = imgStats.mean

    roundedColor = []
    for color in averageColor:
        roundedColor.append(round(color))

    return tuple(roundedColor)


def LoadImageAsCopy(filepath):
    if filepath == None:
        return None
    return Image.open(filepath).copy().convert("RGBA")


def SaveGif(frames, framerate):
    frameDurationMs = (1 / framerate) * 1000

    frames[0].save("output.gif", save_all=True,
                   append_images=frames[1:], loop=0, duration=frameDurationMs, transparency=255, disposal="2")


def LoadAnimationAsFrames(filepath):
    if filepath == None:
        return None

    sequence = ImageSequence.all_frames(
        Image.open(filepath))

    convertedSequence = []

    for image in sequence:
        convertedSequence.append(image.convert("RGBA"))

    return convertedSequence


def FindFramerate(image):
    minFrameDuration = image.info["duration"]

    if not isinstance(minFrameDuration, int):
        minFrameDuration = min(minFrameDuration)

    return 1 / (minFrameDuration / 1000)


class AnimatedMosaicGenerator():
    def __init__(self, inputImagePath, tileImagePath, tileOffsetImagePath, outputImagePath, tileDensityWidth, inputImageFramerate, tileImageFramerate, maxFramerateStretch, maxRepetitions, tileAnimationOffsetStrength) -> None:
        self.inputImage = LoadImageAsCopy(inputImagePath)
        self.tileImage = LoadImageAsCopy(tileImagePath)
        self.tileOffsetImage = LoadImageAsCopy(tileOffsetImagePath)

        self.inputImageFrames = LoadAnimationAsFrames(inputImagePath)
        self.tileImageFrames = LoadAnimationAsFrames(tileImagePath)
        self.tileOffsetImageFrames = LoadAnimationAsFrames(tileOffsetImagePath)

        self.outputImagePath = outputImagePath

        self.tileDensityWidth = tileDensityWidth

        if inputImageFramerate == None:
            self.inputImageFramerate = FindFramerate(self.inputImage)
        else:
            self.inputImageFramerate = inputImageFramerate

        if tileImageFramerate == None:
            self.tileImageFramerate = FindFramerate(self.tileImage)
        else:
            self.tileImageFramerate = tileImageFramerate

        self.maxFramerateStretch = maxFramerateStretch

        self.maxRepetitions = maxRepetitions

        self.tileAnimationOffsetStrength = tileAnimationOffsetStrength

    def SetupMosaicGeneration(self):
        self.mosaic = Mosaic(self.tileDensityWidth,
                             self.inputImageFrames[0],
                             self.tileImageFrames[0])

        self.animations = [
            frame_align.Animation(
                len(self.inputImageFrames), self.inputImageFramerate),
            frame_align.Animation(
                len(self.tileImageFrames), self.tileImageFramerate)]

        alignedFrames = frame_align.AlignFrames(
            self.animations[0], self.animations[1], self.maxFramerateStretch, self.maxRepetitions)

        self.frameNumbers = alignedFrames["frames"]
        self.outputFramerate = alignedFrames["framerate"]

        return len(self.frameNumbers)

    def GenerateMosaicFrames(self):
        self.frames = []

        for frame in self.frameNumbers:
            self.frames.append(CreateOffsetMosaic(
                self.mosaic, self.tileImageFrames, self.inputImageFrames[frame[0]], self.tileAnimationOffsetStrength, frame[1]))

        return len(self.frames)

    def SaveMosaic(self):
        SaveGif(self.frames, self.outputFramerate)


if __name__ == "__main__":
    args = launch_command_config.GetArguments()

    animatedMosaicGenerator = AnimatedMosaicGenerator(
        args.inputImagePath,
        args.tileImagePath,
        args.animationOffsetImagePath,
        args.outputImagePath,
        args.tileResolution,
        args.inputImageFramerate,
        args.tileImageFramerate,
        args.maxFramerateStretch,
        args.maxRepetitions,
        args.tileAnimationOffsetStrength)

    animatedMosaicGenerator.SetupMosaicGeneration()
    animatedMosaicGenerator.GenerateMosaicFrames()
    animatedMosaicGenerator.SaveMosaic()
