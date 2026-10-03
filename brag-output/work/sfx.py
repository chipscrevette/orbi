"""Les bruitages du film, en stéréo, façon interface haut de gamme : chaque son est fait de couches (une attaque
douce, un corps filtré, parfois un grave), passe par une même réverbération de pièce, et a sa place gauche-droite.
Les hauteurs restent dans la tonalité de la musique (do majeur)."""
import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
rng = np.random.default_rng(11)


def note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def filtre(x, genre, f, ordre=2):
    return sosfilt(butter(ordre, f, btype=genre, fs=SR, output="sos"), x)


def env(n, attaque, chute, courbe=1.0):
    a = np.minimum(1, np.arange(n) / max(1, int(attaque * SR)))
    return a * np.exp(-(np.arange(n) / (chute * SR)) ** courbe)


def secondes(d):
    return np.arange(int(d * SR)) / SR


def stereo(x, pan=0.0, largeur=0.0):
    """pan de -1 (gauche) à 1 (droite) ; largeur : un léger décalage de 0 à 1 ms entre les canaux."""
    g, d = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    k = int(largeur * 0.001 * SR)
    droite = np.concatenate([np.zeros(k), x])[: len(x)] if k else x
    return np.stack([x * g * 1.41, droite * d * 1.41], axis=1)


# ---------------------------------------------------------------- les sons
def tok(f=1400, pan=0.0):
    """Un « tok » de bois feutré : le mot du titre qui se pose."""
    x = secondes(0.18)
    corps = np.sin(2 * np.pi * f * x) * env(len(x), 0.001, 0.025) + 0.5 * np.sin(2 * np.pi * f * 2.76 * x) * env(len(x), 0.001, 0.01)
    souffle = filtre(rng.standard_normal(len(x)), "bandpass", [f * 0.8, f * 3]) * env(len(x), 0.0005, 0.006)
    return stereo(corps * 0.6 + souffle * 0.25, pan, 0.3)


def touche(pan=-0.15):
    """Une touche de clavier mécanique silencieux : un clic court et assourdi."""
    x = secondes(0.05)
    clic = filtre(rng.standard_normal(len(x)), "bandpass", [1800, 5200]) * env(len(x), 0.0003, 0.004)
    bas = np.sin(2 * np.pi * 320 * x) * env(len(x), 0.0005, 0.008)
    return stereo(clic * 0.5 + bas * 0.25, pan + rng.uniform(-0.1, 0.1))


def coche(midi, pan=0.2):
    """Une étape cochée : un marimba de verre (partiels inharmoniques), brillant mais doux."""
    f = note(midi)
    x = secondes(0.6)
    son = (np.sin(2 * np.pi * f * x) * env(len(x), 0.002, 0.18)
           + 0.35 * np.sin(2 * np.pi * f * 3.93 * x) * env(len(x), 0.001, 0.05)
           + 0.15 * np.sin(2 * np.pi * f * 9.5 * x) * env(len(x), 0.0005, 0.015))
    return stereo(son * 0.5, pan, 0.4)


def souffle(duree=0.5, de=400, a=5000, pan_de=-0.6, pan_a=0.6):
    """Un passage d'air qui traverse l'image (bruit filtré dont la fréquence et la position glissent)."""
    n = int(duree * SR)
    b = rng.standard_normal(n)
    morceaux, pas = [], 512
    for i in range(0, n, pas):
        k = i / n
        f = de * (a / de) ** k
        morceaux.append(filtre(b[i:i + pas], "bandpass", [f * 0.7, min(f * 1.4, SR / 2 - 100)], 1))
    x = np.concatenate(morceaux)[:n] * np.sin(np.linspace(0, np.pi, n)) ** 1.5
    g = np.linspace(pan_de, pan_a, n)
    return np.stack([x * np.cos((g + 1) * np.pi / 4), x * np.sin((g + 1) * np.pi / 4)], axis=1) * 0.5


def impact(grave=55, poids=1.0):
    """Un impact feutré : une brique qui se pose, un verdict qui tombe. Un grave rond, une bouffée d'air, un bois."""
    x = secondes(0.6)
    sub = np.sin(2 * np.pi * np.cumsum(grave + grave * 1.5 * np.exp(-x * 30)) / SR) * env(len(x), 0.002, 0.18)
    air = filtre(rng.standard_normal(len(x)), "lowpass", 900) * env(len(x), 0.001, 0.04)
    bois = np.sin(2 * np.pi * 190 * x) * env(len(x), 0.001, 0.03)
    return stereo((sub * 0.9 + air * 0.35 + bois * 0.2) * poids, 0.0, 0.2)


def cloche(midis, duree=2.4, eclat=1.0):
    """Une cloche de verre (synthèse FM douce) : un accord qui s'ouvre."""
    x = secondes(duree)
    son = np.zeros(len(x))
    for k, m in enumerate(midis):
        f = note(m)
        indice = 2.2 * np.exp(-x / 0.25) * eclat
        son += np.sin(2 * np.pi * f * x + indice * np.sin(2 * np.pi * f * 3.5 * x)) * env(len(x), 0.004 + k * 0.01, duree * 0.38)
    return stereo(son / len(midis), 0.0, 0.6)


def tampon():
    """« Vérifiée mot à mot » : un tampon encreur, sec, avec son petit claquement de papier."""
    x = secondes(0.25)
    choc = np.sin(2 * np.pi * 140 * x) * env(len(x), 0.001, 0.035)
    papier = filtre(rng.standard_normal(len(x)), "highpass", 2500) * env(len(x), 0.0005, 0.012)
    return stereo(choc * 0.7 + papier * 0.25, -0.1, 0.2)


def pop_carte(midi, pan):
    """Une carte qui arrive : un petit souffle puis un pop rond accordé."""
    x = secondes(0.35)
    f = note(midi)
    pop = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.6 * np.exp(-x * 60))) / SR) * env(len(x), 0.001, 0.07)
    return stereo(pop * 0.45, pan, 0.3)


# ---------------------------------------------------------------- la pièce : une réverbération commune
def reverb(signal, duree=1.4, melange=0.22):
    n = int(duree * SR)
    ir = np.stack([rng.standard_normal(n), rng.standard_normal(n)], axis=1) * np.exp(-np.arange(n) / (0.32 * SR))[:, None]
    ir[:, 0] = filtre(ir[:, 0], "lowpass", 6000)
    ir[:, 1] = filtre(ir[:, 1], "lowpass", 6000)
    ir /= np.sqrt(np.sum(ir ** 2, axis=0))
    mouille = np.stack([fftconvolve(signal[:, c], ir[:, c])[: len(signal)] for c in range(2)], axis=1)
    return signal * (1 - melange) + mouille * melange * 2.2
