# Underlag

Källfiler som skripten i `verktyg/` läser. Filerna visas aldrig i appen; appen hänvisar till de publicerade källorna i
`road2zero/data/referenser.csv`.

| Fil | Läses av | Ger |
|---|---|---|
| `tabell_a_utokad.xlsx` | `python verktyg/las_tabell_a.py` | Startvärden per byggnadstyp och stomme, reduktionskurvor och standardtakter för byggpåverkan |

Byt ut filen mot en ny version med samma bladnamn och kör skriptet och testerna. Håll repot privat om filerna inte ska vara offentliga.
