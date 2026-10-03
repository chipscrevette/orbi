"""La bande-son du film (20 s), musique et bruitages écrits ensemble : 120 bpm, do majeur, mixés doux.
Les bruitages tombent sur les événements de film.html (frappe, étapes cochées, verdict, cartes, fin)."""
import wave

import numpy as np

SR, DUREE = 44100, 20.0
N = int(SR * DUREE)
t = np.arange(N) / SR
BEAT = 0.5  # 120 bpm


def note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def place(sortie, signal, debut, gain=1.0):
    i = int(debut * SR)
    j = min(N, i + len(signal))
    if i < N:
        sortie[i:j] += gain * signal[: j - i]


def enveloppe(n, attaque, chute):
    a = np.minimum(1, np.arange(n) / max(1, int(attaque * SR)))
    return a * np.exp(-np.arange(n) / (chute * SR))


def douce(f, duree, harmoniques=(1, 0.35, 0.15)):
    x = np.arange(int(duree * SR)) / SR
    return sum(a * np.sin(2 * np.pi * f * (k + 1) * x) for k, a in enumerate(harmoniques))


musique = np.zeros(N)
bruit = np.zeros(N)
# grille d'accords : une mesure (2 s) chacun
ACCORDS = [[53, 57, 60, 64], [55, 59, 62, 67], [52, 55, 59, 62], [57, 60, 64, 67], [53, 57, 60, 64],
           [55, 59, 62, 65], [48, 52, 55, 60], [53, 57, 60, 64], [55, 59, 62, 67], [48, 52, 55, 60]]
for m, accord in enumerate(ACCORDS):
    debut = m * 2.0
    # nappe : quatre notes douces, légèrement désaccordées
    for k, n in enumerate(accord):
        nappe = (douce(note(n), 2.1) + douce(note(n) * 1.004, 2.1)) * enveloppe(int(2.1 * SR), 0.25, 2.5)
        place(musique, nappe, debut, 0.05)
    # basse
    place(musique, douce(note(accord[0] - 12), 2.0, (1, 0.2)) * enveloppe(int(2.0 * SR), 0.02, 0.9), debut, 0.16)
    # arpège pincé en croches, à partir de la mesure 2
    if m >= 1:
        motif = [accord[0] + 12, accord[1] + 12, accord[2] + 12, accord[3] + 12, accord[2] + 12, accord[1] + 12, accord[2] + 12, accord[3] + 12]
        for i, n in enumerate(motif):
            pince = douce(note(n), 0.4, (1, 0.5, 0.2, 0.1)) * enveloppe(int(0.4 * SR), 0.003, 0.11)
            place(musique, pince, debut + i * BEAT / 2, 0.06)
# pied doux sur les temps (scènes 2 à 4), charleston léger à contretemps
rng = np.random.default_rng(7)
for b in np.arange(3.0, 16.5, BEAT):
    n = int(0.25 * SR)
    x = np.arange(n) / SR
    f = 50 + 70 * np.exp(-x * 30)
    place(musique, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 14), b, 0.28)
    hh = rng.standard_normal(int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / (0.008 * SR))
    place(musique, np.diff(hh, prepend=0), b + BEAT / 2, 0.025)


def clic(gain=0.03):
    n = int(0.02 * SR)
    return np.diff(rng.standard_normal(n), prepend=0) * np.exp(-np.arange(n) / (0.003 * SR)) * gain


# frappe : le titre (0,15 → 1,05 s) et la question (3,35 → 4,55 s)
for a, b, nb in ((0.15, 1.05, 24), (3.35, 4.55, 40)):
    for x in np.linspace(a, b, nb):
        place(bruit, clic(), x + rng.uniform(-0.01, 0.01))
# pling des étapes cochées : notes de l'accord en cours (fa majeur, puis sol)
for x, n in ((5.15, 72), (5.45, 76), (5.75, 79), (6.95, 81), (7.12, 84), (7.28, 88)):
    place(bruit, douce(note(n), 0.5, (1, 0.2)) * enveloppe(int(0.5 * SR), 0.002, 0.12), x, 0.07)
# envoi, verdict, « vérifiée mot à mot », cartes de la preuve
place(bruit, douce(note(67), 0.3, (1, 0.3)) * enveloppe(int(0.3 * SR), 0.002, 0.06), 4.7, 0.08)
for k, n in enumerate((72, 76, 79, 84)):
    place(bruit, douce(note(n), 1.2, (1, 0.25)) * enveloppe(int(1.2 * SR), 0.004, 0.45), 7.85 + k * 0.05, 0.05)
place(bruit, douce(note(91), 0.6, (1, 0.1)) * enveloppe(int(0.6 * SR), 0.002, 0.18), 10.35, 0.05)
for x, n in ((13.45, 76), (13.7, 79), (13.95, 84)):
    place(bruit, douce(note(n), 0.6, (1, 0.3)) * enveloppe(int(0.6 * SR), 0.003, 0.15), x, 0.07)
# souffles de transition (bruit filtré qui monte puis retombe)
for x in (2.75, 12.75, 16.3):
    n = int(0.6 * SR)
    s = np.convolve(rng.standard_normal(n), np.ones(40) / 40, mode="same") * np.sin(np.linspace(0, np.pi, n)) ** 2
    place(bruit, s, x, 0.25)
# chute de la brique : un petit « bomp » doux (début et fin), puis la cloche finale
for x in (0.8, 17.05):
    n = int(0.3 * SR)
    xx = np.arange(n) / SR
    place(bruit, np.sin(2 * np.pi * np.cumsum(90 + 120 * np.exp(-xx * 25)) / SR) * np.exp(-xx * 12), x, 0.3)
for k, n in enumerate((60, 64, 67, 72, 76)):
    place(bruit, douce(note(n), 3.0, (1, 0.3, 0.1)) * enveloppe(int(3.0 * SR), 0.01, 1.2), 17.2 + k * 0.03, 0.045)

mix = musique + bruit
mix *= np.minimum(1, t / 0.3) * np.minimum(1, (DUREE - t) / 1.5)  # entrée et sortie en fondu
mix = np.tanh(mix * 1.6) / np.tanh(1.6)                             # limiteur doux
mix *= 0.89 / np.max(np.abs(mix))                                   # crête à -1 dB
stereo = np.stack([mix, np.roll(mix, 220) * 0.98], axis=1)          # un peu d'espace
with wave.open("musique.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype("<i2").tobytes())
print("musique.wav", DUREE, "s")
