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

# bruitages haut de gamme (sfx.py), en stéréo, posés sur les événements de film.js
import sfx as S  # noqa: E402

effets = np.zeros((N, 2))


def poser(son, debut, gain=1.0):
    i = int(debut * SR)
    j = min(N, i + len(son))
    if 0 <= i < N:
        effets[i:j] += gain * son[: j - i]


for i in range(3):  # les trois mots du titre
    poser(S.tok(1250 + 180 * i, pan=-0.3 + 0.3 * i), 0.12 + i * TEMPS * 0.75, 0.7)
poser(S.souffle(0.35, 2500, 500, 0.2, -0.1), 0.62, 0.15)  # la brique qui tombe…
poser(S.impact(52), 1.27, 0.32)                           # …et qui se pose
for x in np.linspace(2.9, 3.75, 22):                     # la frappe
    poser(S.touche(), x + rng.uniform(-0.012, 0.012), 0.3 + rng.uniform(0, 0.15))
poser(S.souffle(0.3, 600, 6000, -0.2, 0.5), 3.72, 0.15)  # envoi
for x, m, pan in ((4.3, 79, -0.2), (4.53, 83, 0.0), (4.77, 86, 0.2), (5.7, 88, 0.1), (5.85, 91, 0.25), (6.0, 95, 0.35)):
    poser(S.coche(m, pan), x, 0.55)                       # les étapes cochées, en montant
poser(S.impact(46), 6.5, 0.38)                       # le verdict tombe
poser(S.cloche([60, 64, 67, 71, 74], 2.2), 6.5, 0.4)
poser(S.tampon(), 8.2, 1.0)                              # « vérifiée mot à mot »
for x in (2.32, 10.82, 14.62):                           # les changements de scène
    poser(S.souffle(0.45, 350, 4000, -0.5, 0.5), x, 0.14)
for x, m, pan in ((11.6, 72, -0.4), (11.6 + TEMPS, 76, 0.0), (11.6 + 2 * TEMPS, 79, 0.4)):
    poser(S.pop_carte(m, pan), x, 0.6)                   # les trois cartes
poser(S.impact(50), 15.32, 0.3)                          # la brique finale
poser(S.cloche([48, 60, 64, 67, 72, 76], 2.6, 0.7), 15.45, 0.45)

effets = S.reverb(effets, melange=0.14)
# la musique accompagne, les bruitages racontent : la musique bien en retrait
mix = np.stack([musique, np.roll(musique, 220) * 0.98], axis=1) * 0.6 + effets * 1.0
mix *= (np.minimum(1, t / 0.05) * np.minimum(1, (DUREE - t) / 1.2))[:, None]
mix *= 0.7 / np.max(np.abs(mix))  # marge : loudnorm fixe le volume final
with wave.open("musique.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("musique.wav", DUREE, "s")
