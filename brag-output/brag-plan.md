# Orbi · le film de 20 secondes

**Ce que c'est** : un assistant d'urbanisme qui tourne sur votre ordinateur. On lui demande « puis-je construire ça, à cette adresse de Biarritz ? », il répond oui, non ou sous conditions, et cite le règlement mot à mot avec la page.
**Pour qui** : un particulier qui a un projet (abri, extension, piscine, clôture) et ne veut pas lire 200 pages de PLU.
**Ce qui le distingue** : le modèle lit, le code vérifie. Chaque citation est contrôlée mot à mot avant d'être montrée, et le score est mesuré sur des questions jamais vues (27/40, honnête).
**L'accroche** : la question que tout le monde se pose, « Puis-je construire ici ? », et une brique bleue qui tombe dans le cadre.
**Ton** : `default` (net, joueur, propre), aux couleurs de l'appli.
**Légende à partager** : voir share-copy.txt.

## Découpage (1920×1080, 30 i/s, 20 s)
| scène | temps | ce qu'on voit |
|---|---|---|
| 1. Accroche | 0 → 3 s | « Puis-je construire ici ? » s'écrit ; la brique Orbi tombe et s'écrase un peu ; « Orbi a lu tout le PLU de Biarritz. » |
| 2. La question | 3 → 7,5 s | la fenêtre de l'appli ; la vraie question s'écrit (abri de jardin de 10 m², 15 avenue de la Marne) ; envoi ; les 6 étapes se cochent, le minuteur file jusqu'à 1 min 19 s (temps réel sur la RTX 3060) |
| 3. La réponse | 7,5 → 13 s | « Oui, sous conditions » ; parcelle AB 0073 · zone UAs · site patrimonial ; la citation de l'UA 7, « vérifiée mot à mot », p. 21 ; la vraie carte des zones autour de la parcelle ; la démarche (déclaration préalable, 2 mois) |
| 4. La preuve | 13 → 16,5 s | « Le modèle lit. Le code vérifie. » ; trois cartes : 100 % sur votre machine · 1 108 tests · 27/40 sur des questions jamais vues |
| 5. Fin | 16,5 → 20 s | Orbi en grand, « Votre projet. Le PLU. Article par article. », github.com/chipscrevette/orbi |

Toutes les données viennent d'une vraie réponse enregistrée le 3 octobre 2026 (conversations/20261003-043737-276235.jsonl) et des vraies zones du PLU (donnees/zones-biarritz.geojson).

## Son
Une piste unique à 120 bpm en do majeur : nappe douce, arpège pincé, pied léger à partir de la scène 2 ; les petits clics de frappe, les « pling » des étapes (notes de l'accord en cours), un « pop » sur le verdict et une cloche finale, mixés sous la musique.

## Version 2 (rythmée, 18 s)
Calée sur une pulsation à 128 bpm : les trois mots du titre tombent sur trois temps, la brique sur le quatrième ; les
scènes entrent et sortent en glissant (0,25 s) avec une lente poussée de caméra ; les étapes se cochent sur les croches ;
une respiration de la batterie juste avant que le verdict claque ; les trois cartes de la preuve arrivent sur trois temps.
Son : -16 LUFS intégrés, crête vraie à -1,5 dB (ffmpeg loudnorm), au lieu de -12 LUFS écrasés dans la version 1.
