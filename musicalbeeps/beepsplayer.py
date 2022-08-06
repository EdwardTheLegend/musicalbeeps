#!/usr/bin/env python3

import os
import sys
import time
from typing import Union
import numpy as np
import simpleaudio as sa

from musicalbeeps.script import player_loop


class Player:
    def __init__(self, volume: float = 0.3, mute_output: bool = False):

        if volume < 0 or volume > 1:
            raise ValueError("Volume must be a float between 0 and 1")

        # Frequencies for the lowest octave
        self.note_frequencies = {
            "A": 27.50000,
            "B": 30.86771,
            "C": 16.35160,
            "D": 18.35405,
            "E": 20.60172,
            "F": 21.82676,
            "G": 24.49971,
        }

        self.volume = volume
        self.mute_output = mute_output
        self.rate = 44100
        self.freq = 0
        self.fade = 800
        self._valid_note = True
        self._fade_in = np.arange(0.0, 1.0, 1 / self.fade)
        self._fade_out = np.arange(1.0, 0.0, -1 / self.fade)
        self._play_obj = None
        self._destructor_sleep = 0

    def __set_base_frequency(self, note: str):
        letter = note[:1].upper()
        try:
            self.freq = self.note_frequencies[letter]
        except:
            self._valid_note = False
            print("Error: invalid note: '" + note[:1] + "'", file=sys.stderr)

    def __set_octave(self, octave: str = "4"):
        if not self._valid_note:
            return
        try:
            octaveValue = int(octave)
            if octaveValue < 0 or octaveValue > 8:
                raise ValueError("octave value error")
            self.freq *= 2**octaveValue
        except:
            self._valid_note = False
            print("Error: invalid octave: '" + octave + "'", file=sys.stderr)

    def __set_semitone(self, symbol: str):
        if not self._valid_note:
            return
        if symbol == "#":
            self.freq *= 2 ** (1.0 / 12.0)
        elif symbol == "b":
            self.freq /= 2 ** (1.0 / 12.0)
        else:
            self._valid_note = False
            print("Error: invalid symbol: '" + symbol + "'", file=sys.stderr)

    def __calc_frequency(self, note: str):
        self.__set_base_frequency(note)
        if len(note) == 1:
            self.__set_octave()
        elif len(note) == 2:
            if note[1:2] == "#" or note[1:2] == "b":
                self.__set_octave()
                self.__set_semitone(note[1:2])
            else:
                self.__set_octave(note[1:2])
        elif len(note) == 3:
            self.__set_octave(note[1:2])
            self.__set_semitone(note[2:3])
        else:
            if self._valid_note:
                print("Errror: invalid note: '" + note + "'", file=sys.stderr)
                self._valid_note = False

    def __wait_for_prev_sound(self):
        if self._play_obj is not None:
            while self._play_obj.is_playing():
                pass

    def __write_stream(self, duration: float = 0.5, audio=None):
        if audio is None:
            audio = self.generate_note_waveform(duration)

        self.__wait_for_prev_sound()
        self._play_obj = sa.play_buffer(audio, 1, 2, self.rate)

    def generate_note_waveform(
        self, duration, wave_variation_mutlipliers=np.linspace(-10, 2, num=5)
    ):
        t = np.linspace(0, duration, int(duration * self.rate), False)

        # generate sine wave at different fractions of the frequency
        waves = np.zeros(len(t))
        for i in wave_variation_mutlipliers:
            waves = np.vstack([waves, np.sin(2 * np.pi * self.freq * t * i)])

        # average the waves to get the final waveform
        audio = np.mean(waves, axis=0)

        audio *= 32767 / np.max(np.abs(audio))
        audio *= self.volume

        if len(audio) > self.fade:
            audio[: self.fade] *= self._fade_in
            audio[-self.fade :] *= self._fade_out

        audio = audio.astype(np.int16)

        return audio

    def __print_played_note(self, note: str, duration: float):
        if self.mute_output or not self._valid_note:
            return
        if note == "pause":
            print("Pausing for " + str(duration) + "s")
        else:
            print(
                "Playing "
                + note
                + " ("
                + format(self.freq, ".2f")
                + " Hz) for "
                + str(duration)
                + "s"
            )

    def play_note(self, note: str, duration: float = 0.5):
        self._valid_note = True
        if note == "pause":
            self.__wait_for_prev_sound()
            self.__print_played_note(note, duration)
            time.sleep(duration)
            self._destructor_sleep = 0
        else:
            self.__calc_frequency(note)
            if self._valid_note:
                self.__write_stream(duration)
                self.__print_played_note(note, duration)
                self._destructor_sleep = duration

    def play_tune(
        self,
        tune: Union[str, list],
        wave_variation_mutlipliers=np.linspace(-10, 2, num=5),
    ):
        if isinstance(tune, str):
            with open(tune, "r") as f:
                audio = self.generate_tune_waveform(
                    f, wave_variation_mutlipliers=wave_variation_mutlipliers
                )
        elif isinstance(tune, list):
            audio = self.generate_tune_waveform(
                tune, wave_variation_mutlipliers=wave_variation_mutlipliers
            )
        else:
            raise TypeError("tune must be a string or list")

        # play audio
        self.__write_stream(audio=audio)

    def generate_tune_waveform(
        self, lines, wave_variation_mutlipliers=np.linspace(-10, 2, num=5)
    ):
        # create waveform for each note in the tune
        notes_waves = []
        for line in lines:
            line = line.strip()
            if len(line) > 0:
                try:
                    note, duration = line.split(":")
                except:
                    note, duration = line, 0.5

                try:
                    duration = float(duration)
                except:
                    duration = 0.5

                self.__calc_frequency(note)
                if self._valid_note:
                    notes_waves.append(
                        self.generate_note_waveform(
                            duration,
                            wave_variation_mutlipliers=wave_variation_mutlipliers,
                        )
                    )

        # combine all notes together
        audio = np.concatenate(notes_waves)

        return audio

    def __del__(self):
        time.sleep(self._destructor_sleep)


default_player = Player()


def play_note(*args, **kwargs):
    default_player.play_note(*args, **kwargs)


def play_tune(*args, **kwargs):
    default_player.play_tune(*args, **kwargs)


if __name__ == "__main__":
    # play test tune
    # play_tune("music_scores/fur_elise.txt")

    play_tune(["E4", "D4"])
