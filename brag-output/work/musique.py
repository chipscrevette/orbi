"""La bande-son du film rythmé (18 s), musique et bruitages écrits ensemble : 128 bpm, do majeur.
Mixée avec de la nuance (pas de compression écrasante) ; le volume final est normalisé à -16 LUFS au montage (ffmpeg loudnorm).
Les bruitages tombent sur les événements de film.js."""
import wave

import numpy as np

SR, DUREE = 44100, 18.0
N = int(SR * DUREE)
t = np.arange(N) / SR
TEMPS = 60 / 128
MESURE = 4 * TEMPS
rng = np.random.default_rng(7)


def note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def place(sortie, signal, debut, gain=1.0):
    i = int(debut * SR)
    j = min(N, i + len(signal))
    if 0 <= i < N:
        sortie[i:j] += gain * signal[: j - i]


def env(n, attaque, chute):
    return np.minimum(1, np.arange(n) / max(1, int(attaque * SR))) * np.exp(-np.arange(n) / (chute * SR))


def ton(f, duree, harm=(1, 0.35, 0.15)):
    x = np.arange(int(duree * SR)) / SR
    return sum(a * np.sin(2 * np.pi * f * (k + 1) * x) for k, a in enumerate(harm))


def bruit_filtre(duree, lissage):
    n = int(duree * SR)
    return np.convolve(rng.standard_normal(n), np.ones(lissage) / lissage, mode="same")


musique = np.zeros(N)
sfx = np.zeros(N)
ACCORDS = [[48, 52, 55, 60], [53, 57, 60, 64], [57, 60, 64, 67], [55, 59, 62, 67],
           [53, 57, 60, 64], [55, 59, 62, 67], [48, 52, 55, 60], [53, 57, 60, 64], [55, 59, 62, 67], [48, 52, 55, 60]]
for m, accord in enumerate(ACCORDS):
    debut = m * MESURE
    if debut >= DUREE:
        break
    for n in accord:  # nappe
        place(musique, (ton(note(n), MESURE + 0.1) + ton(note(n) * 1.004, MESURE + 0.1)) * env(int((MESURE + 0.1) * SR), 0.12, 2.0), debut, 0.035)
    for b in range(4):  # basse pulsée en noires
        place(musique, ton(note(accord[0] - 12), TEMPS, (1, 0.25)) * env(int(TEMPS * SR), 0.005, 0.18), debut + b * TEMPS, 0.2)
    motif = [accord[0] + 12, accord[2] + 12, accord[1] + 24, accord[2] + 12, accord[3] + 12, accord[2] + 12, accord[1] + 24, accord[2] + 12]
    for i, n in enumerate(motif):  # arpège en croches
        place(musique, ton(note(n), 0.3, (1, 0.5, 0.2, 0.1)) * env(int(0.3 * SR), 0.002, 0.08), debut + i * TEMPS / 2, 0.05)


def pied():
    n = int(0.3 * SR)
    x = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(48 + 90 * np.exp(-x * 35)) / SR) * np.exp(-x * 11)


def claque():
    n = int(0.18 * SR)
    b = np.diff(rng.standard_normal(n), prepend=0) * np.exp(-np.arange(n) / (0.035 * SR))
    return np.convolve(b, np.ones(6) / 6, mode="same")


def charley():
    n = int(0.05 * SR)
    return np.diff(rng.standard_normal(n), prepend=0) * np.exp(-np.arange(n) / (0.007 * SR))


# batterie : légère pendant l'accroche, pleine ensuite, une respiration juste avant le verdict
for k in range(int(DUREE / TEMPS) + 1):
    b = k * TEMPS
    if b > 17.0:
        break
    respiration = 5.95 < b < 6.45
    if b >= 0.9 and not respiration:
        place(musique, pied(), b, 0.42 if b >= 2.55 else 0.25)
    if b >= 2.55 and k % 2 == 1 and not respiration:
        place(musique, claque(), b, 0.12)
    if b >= 2.55 and not respiration:
        place(musique, charley(), b + TEMPS / 2, 0.035)

# bruitages, dans la tonalité, sous la musique
for i in range(3):  # les trois mots du titre
    place(sfx, ton(note(72 + 4 * i), 0.25, (1, 0.3)) * env(int(0.25 * SR), 0.002, 0.07), 0.12 + i * TEMPS * 0.75, 0.05)
for x in np.linspace(2.9, 3.75, 30):  # frappe
    n = int(0.015 * SR)
    place(sfx, np.diff(rng.standard_normal(n), prepend=0) * np.exp(-np.arange(n) / (0.002 * SR)), x, 0.012)
for x, n in ((4.3, 72), (4.53, 76), (4.77, 79), (5.7, 81), (5.85, 84), (6.0, 88)):  # étapes cochées
    place(sfx, ton(note(n), 0.35, (1, 0.2)) * env(int(0.35 * SR), 0.002, 0.09), x, 0.05)
for x, n in ((1.27, 0), (15.32, 0)):  # la brique touche le sol
    m = int(0.3 * SR)
    xx = np.arange(m) / SR
    place(sfx, np.sin(2 * np.pi * np.cumsum(80 + 120 * np.exp(-xx * 25)) / SR) * np.exp(-xx * 12), x, 0.3)
for k, n in enumerate((60, 64, 67, 72)):  # le verdict : un accord frappé
    place(sfx, ton(note(n), 1.0, (1, 0.3)) * env(int(1.0 * SR), 0.003, 0.4), 6.5 + k * 0.012, 0.06)
place(sfx, pied(), 6.5, 0.5)
place(sfx, ton(note(91), 0.4, (1, 0.1)) * env(int(0.4 * SR), 0.002, 0.12), 8.2, 0.04)  # « vérifiée mot à mot »
for x, n in ((11.6, 76), (11.6 + TEMPS, 79), (11.6 + 2 * TEMPS, 84)):  # les trois cartes
    place(sfx, ton(note(n), 0.4, (1, 0.3)) * env(int(0.4 * SR), 0.002, 0.1), x, 0.05)
for x in (2.3, 10.85, 14.65):  # souffles avant chaque changement de scène
    s = bruit_filtre(0.45, 30) * np.sin(np.linspace(0, np.pi / 2, int(0.45 * SR))) ** 2
    place(sfx, s, x, 0.18)
for k, n in enumerate((60, 64, 67, 72, 76)):  # la cloche finale
    place(sfx, ton(note(n), 2.6, (1, 0.3, 0.1)) * env(int(2.6 * SR), 0.01, 1.0), 15.4 + k * 0.03, 0.035)

mix = musique + sfx
mix *= np.minimum(1, t / 0.05) * np.minimum(1, (DUREE - t) / 1.2)
mix *= 0.7 / np.max(np.abs(mix))  # marge : loudnorm fixe le volume final
stereo = np.stack([mix, np.roll(mix, 220) * 0.98], axis=1)
with wave.open("musique.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype("<i2").tobytes())
print("musique.wav", DUREE, "s")
