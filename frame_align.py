from __future__ import annotations
import math
from decimal import Decimal
from typing import TypedDict

class searchResult(TypedDict):
    gif1reps: int
    gif2reps: int
    difference: float

def FindOptimalRepetitions(gif1Duration: float, gif2Duration: float, maxStretch: float, maxRepetitions: int) -> searchResult:
    searchResults: list[searchResult] = []

    for i in range(maxRepetitions):
        gif1Repetitions = i + 1
        gif2Repetitions = round(gif1Duration * gif1Repetitions / gif2Duration)

        difference = float((Decimal(str(gif2Duration)) * Decimal(str(gif2Repetitions))) /
                           (Decimal(str(gif1Duration)) * Decimal(str(gif1Repetitions))))

        searchResults.append(
            {
                "gif1reps": gif1Repetitions,
                "gif2reps": gif2Repetitions,
                "difference": difference,
            }
        )

        if abs(difference - 1) < maxStretch:
            break

    sortedSearchResults = sorted(
        searchResults, key=lambda item: abs(item["difference"] - 1))

    return sortedSearchResults[0]


def FindOptimalAnimationSettings(animation1: Animation, animation2: Animation) -> tuple[int, float]:
    return max(animation1.frames * animation1.repetitions, animation2.frames * animation2.repetitions), max(animation1.framerate, animation2.framerate)


class Animation:
    def __init__(self, frames: int, framerate: float, repetitions: int =0) -> None:
        self.frames = frames
        self.framerate = framerate
        self.repetitions = repetitions

    def Duration(self):
        return self.frames / self.framerate

    def RepetitionFrames(self):
        return self.frames * self.repetitions

    def SampleFrameAtTime(self, sampleTime: float):
        framerateAdjustedSampleTime = sampleTime * self.framerate

        sampledFrame = math.floor(
            framerateAdjustedSampleTime) % self.frames
        return sampledFrame

class AlignedConfig(TypedDict):
    frames: list[tuple[int, int]]
    framerate: float

def AlignFrames(animation1: Animation, animation2: Animation, maxStretch: float, maxRepetitons: int) -> AlignedConfig:

    optimalRepetitions = FindOptimalRepetitions(
        animation1.Duration(), animation2.Duration(), maxStretch, maxRepetitons)

    Animation1Loop = Animation(
        animation1.frames,
        animation1.framerate,
        repetitions=optimalRepetitions["gif1reps"])

    Animation2Loop = Animation(
        animation2.frames,
        animation2.framerate * optimalRepetitions["difference"],
        repetitions=optimalRepetitions["gif2reps"])

    optimalFrames, optimalSamplerate = FindOptimalAnimationSettings(
        Animation1Loop, Animation2Loop)

    frames: list[tuple[int, int]] = []

    for frame in range(optimalFrames):
        time = frame / optimalSamplerate

        frames.append((Animation1Loop.SampleFrameAtTime(time),
                       Animation2Loop.SampleFrameAtTime(time)))

    return {"frames": frames,
            "framerate": optimalSamplerate}
