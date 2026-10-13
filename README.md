# SAF-T-validator

Lokal testvalidator fra Agaas, fork av [Skatteetaten/saf-t](https://github.com/Skatteetaten/saf-t).
Filer sendes ikke over nett. CI installerer den lille wheel-filen fra en
[versjonert utgivelse](https://github.com/AgaasNO/saf-t-validator/releases), uten å klone repoet.

I dette repoet, med [Pixi](https://pixi.sh) installert:

```sh
pixi install --locked
pixi run agaas-saft validate eksport.xml --schema-version 1.40
pixi run agaas-saft validate eldre.xml --schema-version 1.30
pixi run agaas-saft validate eldre.xml --schema-version 1.30 --codelist-year 2026
pixi run agaas-saft accounts kontokoblinger.json --catalogue lisensiert-kontoplan.json
pixi run check
pixi run build
```

Bruk 1.40 for regnskapsår fra 2027. 1.30 støttes for eldre eksport.
Begge kommandoer tar `-` som filnavn for stdin og skriver én JSON-rapport.
Returkode `0` betyr beståtte valgte kontroller, `1` ugyldige data, `2` feil i oppsett eller kjøring.

XSD-kontroll er alltid aktiv. Valgfri kodelistekontroll dekker næringsspesifikasjon
og standard MVA-koder for 2025–2026. 2027-listen er ikke publisert i kildeutvalget;
å be om den gir feil. NS 4102:2023-koblinger kontrolleres mot katalogen du leverer.
Ingen lisensiert NS-kontoplan følger med. Dette er ikke en full samsvarsvurdering.

[Grensesnitt og CI](docs/interface.md) · [Eldre regnskap ved onboarding](docs/onboarding.md) ·
[Kilder og avgrensning](docs/sources.md)
