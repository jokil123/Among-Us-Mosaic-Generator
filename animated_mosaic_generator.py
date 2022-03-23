from __future__ import annotations
from typing import TypedDict, Union
from PIL import Image, ImageStat, ImageChops, ImageSequence
import math
import frame_align
import concurrent.futures
import launch_command_config
from recordclass import RecordClass

class TileTransform(TypedDict):
    tilePosition: IntTuple2
    tileBoundingBox: IntTuple4

class ImageSplit(TypedDict):
    image: Image.Image
    position: int

class IntTuple2(RecordClass):
    i0: int
    i1: int

    def AsTuple(self) -> tuple[int, int]:
        return (self.i0, self.i1)
    

class IntTuple4(RecordClass):
    i0: int
    i1: int
    i2: int
    i3: int

    def AsTuple(self) -> tuple[int, int, int, int]:
        return (self.i0, self.i1, self.i2, self.i3)

class FloatTuple4(RecordClass):
    f0: float
    f1: float
    f2: float
    f3: float

    def AsTuple(self) -> tuple[float, float, float, float]:
        return (self.f0, self.f1, self.f2, self.f3)

class Mosaic:
    tiles = IntTuple2(0, 0)
    tileSize = IntTuple2(0, 0)
    outputImageSize = IntTuple2(0, 0)
    pixelRatio: float = 1

    def __init__(self, tileDensity: int, inputImage: Image.Image, tileImage: Image.Image):
        self.tiles[0] = tileDensity
        self.tileImage = tileImage
        self.inputImage = inputImage

        self.CalculateDimensions()

    def CalculateDimensions(self):
        self.outputImageSize[0] = self.tileImage.width * self.tiles[0]
        self.pixelRatio = self.outputImageSize[0] / self.inputImage.width
        self.outputImageSize[1] = self.inputImage.height * self.pixelRatio
        self.tiles[1] = math.floor(
            self.outputImageSize.i1 / self.tileImage.height)
        bottomMargin: float = self.outputImageSize[1] % self.tileImage.height
        verticalMargin: float = bottomMargin / self.tiles[1]

        self.tileSize[0] = self.tileImage.width
        self.tileSize[1] = math.floor(self.tileImage.height + verticalMargin)

        self.outputImageSize[1] = math.ceil(self.outputImageSize.i1)

        self.tileTransforms = self.GetMosaicTileTransforms(
            self.tiles, self.tileSize)

    def InputImageCoord(self, position: int) -> float:
        return position / self.pixelRatio

    def InputImageCoords(self, positions: IntTuple4) -> FloatTuple4:
        inputImageCoords: list[float] = []
        for position in positions.AsTuple():
            inputImageCoords.append(self.InputImageCoord(position))

        return FloatTuple4(inputImageCoords[0], inputImageCoords[1], inputImageCoords[2], inputImageCoords[3])

    def GetMosaicTileTransforms(self, tiles: tuple[int, int], tileSize: tuple[int, int]) -> list[TileTransform]:
        tileTransforms: list[TileTransform] = []

        for xIndex in range(tiles[0]):
            for yIndex in range(tiles[1]):

                tileStartPosition = (xIndex * tileSize[0],
                                     yIndex * tileSize[1])

                tileEndPosition = (tileStartPosition[0] + tileSize[0],
                                   tileStartPosition[1] + tileSize[1])

                tileBoundingBox: IntTuple4 = IntTuple4(tileStartPosition[0], tileStartPosition[1], tileEndPosition[0], tileEndPosition[1])

                tilePosition: IntTuple2 = IntTuple2(xIndex, yIndex)

                tileTransforms.append({
                    "tilePosition": tilePosition,
                    "tileBoundingBox": tileBoundingBox
                })

        return tileTransforms


def CreateOffsetMosaic(mosaic: Mosaic, tileImageFrames: list[Image.Image], inputImage: Image.Image, animationOffsetStrength: float, animationOffset: float, tileImageAnimationOffsetTexture: Union[Image.Image, None] = None):
    tileImageFrameAmmount = len(tileImageFrames)

    outputImage = Image.new("RGBA", mosaic.outputImageSize.AsTuple())

    splits: list[list[TileTransform]] = []
    splitImages: list[ImageSplit] = []

    for i in range(mosaic.tiles.i1):
        start: int = i * mosaic.tiles[1]
        end: int = start + mosaic.tiles[1]

        splits.append(mosaic.tileTransforms[start:end])

    def CreateSplit(threadId: int):
        tileSplitImage = Image.new(
            "RGBA", (mosaic.tileSize.i0, mosaic.outputImageSize.i1))

        for tile in splits[threadId]:
            tilePosition: IntTuple2 = tile["tilePosition"]
            tileBoundingBox: IntTuple4 = tile["tileBoundingBox"]

            gradientFrameOffset: float

            if tileImageAnimationOffsetTexture == None:
                gradientFrameOffset = (tilePosition.i0 + (mosaic.tiles.i1 - tilePosition.i1)) % tileImageFrameAmmount

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
                "RGBA", (tileBoundingBox.i2, tileBoundingBox.i3), color=color)

            grayscaleTileImageTile = tileImageFrames[frame].convert(
                "LA").convert("RGBA")

            tile = ImageChops.multiply(
                solidColorTile, grayscaleTileImageTile)

            tile.putalpha(tileImageFrames[frame].split()[-1])

            tileSplitImage.paste(tile, (0, tileBoundingBox.i1))

        
        splitImages.append(
        {"image": tileSplitImage, "position": tileBoundingBox.i0})

    with concurrent.futures.ThreadPoolExecutor(max_workers=mosaic.tiles.i0) as executor:
        executor.map(CreateSplit, range(mosaic.tiles.i0))

    for splitImage in splitImages:

        outputImage.paste(splitImage["image"], (splitImage["position"], 0))

    return outputImage


def GetAveragePixelColor(img: Image.Image, box: FloatTuple4) -> tuple[int, int, int, int]:
    cropArea = img.crop(box)
    imgStats: ImageStat.Stat = ImageStat.Stat(cropArea)
    averageColor: list[float] = imgStats.mean

    roundedColor: list[int] = []
    for color in averageColor:
        roundedColor.append(round(color))

    return tuple(roundedColor)


def LoadImageAsCopy(filepath: str):
    # if filepath == None:
    #     raise ValueError("Path is empty!")
    #     return None
    return Image.open(filepath).copy().convert("RGBA")


def SaveGif(frames: list[Image.Image], framerate: float):
    frameDurationMs = (1 / framerate) * 1000

    frames[0].save("output.gif", save_all=True,
                   append_images=frames[1:], loop=0, duration=frameDurationMs, transparency=255, disposal="2")


def LoadAnimationAsFrames(filepath: str):
    # if filepath == None:
    #     raise ValueError("Path is empty!")
    #     return None

    sequence: list[Image.Image] = ImageSequence.all_frames(
        Image.open(filepath))

    convertedSequence: list[Image.Image] = []

    for image in sequence:
        convertedSequence.append(image.convert("RGBA"))

    return convertedSequence


def FindFramerate(image: Image.Image):
    minFrameDuration = image.info["duration"]

    if not isinstance(minFrameDuration, int):
        minFrameDuration = min(minFrameDuration)

    return 1 / (minFrameDuration / 1000)


class AnimatedMosaicGenerator():
    def __init__(self, inputImagePath: str, tileImagePath: str, tileOffsetImagePath: Union[str, None], outputImagePath: Union[str, None], tileDensityWidth: int, inputImageFramerate: Union[float, None], tileImageFramerate: Union[float, None], maxFramerateStretch: float, maxRepetitions: int, tileAnimationOffsetStrength: float) -> None:
        self.inputImage = LoadImageAsCopy(inputImagePath)
        self.tileImage = LoadImageAsCopy(tileImagePath)
        # self.tileOffsetImage = LoadImageAsCopy(tileOffsetImagePath)

        self.inputImageFrames: list[Image.Image] = LoadAnimationAsFrames(inputImagePath)
        self.tileImageFrames: list[Image.Image] = LoadAnimationAsFrames(tileImagePath)
        # self.tileOffsetImageFrames: list[Image.Image] = LoadAnimationAsFrames(tileOffsetImagePath)

        # self.outputImagePath = outputImagePath

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
        self.frames: list[Image.Image] = []

        for frame in self.frameNumbers:
            self.frames.append(CreateOffsetMosaic(
                self.mosaic, self.tileImageFrames, self.inputImageFrames[frame[0]], self.tileAnimationOffsetStrength, frame[1]))

        return len(self.frames)

    def SaveMosaic(self):
        SaveGif(self.frames, self.outputFramerate)


def main():
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


if __name__ == "__main__":
    main()
