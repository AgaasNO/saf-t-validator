# Testgrensesnitt

Grensesnittet kjører som en lokal prosess. Testen sender filinnhold på stdin og
leser JSON fra stdout. Ingen server, legitimasjon eller innsending til Skatteetaten
er nødvendig. Installasjon henter avhengigheter; validering bruker bare lokale data.

## SAF-T

```sh
pixi run agaas-saft validate eksport.xml --schema-version 1.40
pixi run agaas-saft validate - --schema-version 1.30 < eldre.xml
pixi run agaas-saft validate eldre.xml --schema-version 1.30 --codelist-year 2026
pixi run agaas-saft info
```

`--schema-version` er `1.40` som standard. `AuditFileVersion` må samsvare med
valgt versjon. Begge versjoner bruker samme XML-navnerom; navnerommet alene
velger derfor ikke riktig skjema. `xsi:schemaLocation` i innsendt XML overstyrer
aldri det innebygde skjemaet.

`--codelist-year` aktiverer kontroll av kombinasjonen `GroupingCategory` og
`GroupingCode` mot næringsspesifikasjonen og av `StandardTaxCode` mot MVA-listen.
Tilgjengelige år er 2025 og 2026. Året velges uttrykkelig av testen; verktøyet
utleder ikke regnskapsår eller vurderer valg av skatteperiode.
KOSTRA og statlig kontoplan inngår ikke. `NA` for MVA og paret `NA`/`NA` for
kontokoblinger aksepteres som dokumenterte unntaksverdier. Om unntaket faktisk
kan brukes, må vurderes separat.

## Resultat

```json
{
  "interface_version": 1,
  "validator_version": "0.1.0",
  "kind": "saft",
  "status": "valid",
  "checks": {"xml": "passed", "schema": "passed", "code_lists": "not_requested"},
  "issues": [],
  "metadata": {"schema_version": "1.40", "codelist_year": null},
  "truncated": false
}
```

| Returkode | Status | Betydning |
| --- | --- | --- |
| 0 | `valid` | Alle valgte kontroller bestod |
| 1 | `invalid` | Filen eller kontokoblingene feilet en kontroll |
| 2 | `error` | Feil argumenter, manglende fil/katalog, størrelsesgrense eller ustøttet kontroll |

`checks` bruker `passed`, `failed`, `not_run` og `not_requested`. Testen må kreve
`passed` for kontrollene den trenger. `valid` med `code_lists: not_requested`
bekrefter bare XML-format og XSD. Det sier ikke at bokføringen er riktig.

Hvert avvik har `code`, `message`, `line` og `path`. De to siste kan være `null`.
Bruk `code` i tester. Tekst og XPath fra XML-biblioteket er ikke stabile mellom
versjoner. Meldinger gjengir ikke feltverdier fra regnskapet. Maksimalt 100 avvik
returneres; `truncated: true` betyr at flere ble funnet. Maksimal filstørrelse er
64 MiB. DTD-er og eksterne entiteter avvises. Dette er et testverktøy for avgrensede
filer, ikke en strømmevalidator for komplette kundearkiver.

## NS 4102

Katalogen skaffes separat med nødvendige bruksrettigheter. Eksemplet under er
kun syntetiske testdata og hevder ikke at numrene tilhører standarden.

`lisensiert-kontoplan.json`:

```json
{"standard":"NS 4102:2023","source":"syntetisk eksempel","accounts":["10000","20000"]}
```

`kontokoblinger.json`:

```json
{"standard":"NS 4102:2023","mappings":[{"account_id":"lokal-a","standard_account":"10000"}]}
```

```sh
pixi run agaas-saft accounts kontokoblinger.json --catalogue lisensiert-kontoplan.json
```

Kontrollen krever én eksplisitt kobling per innsendt lokal konto og at målkontoen
finnes i katalogen. Flere lokale kontoer kan bruke samme målkonto. Ingen siffer
fjernes eller legges til automatisk. Fire- og femsifrede katalogkoder støttes;
koblingen må bruke nøyaktig samme kode. Tom katalog og dupliserte JSON-nøkler
avvises. Rapporten inneholder SHA-256 for katalogen.

Testen må selv sende hele kontoutvalget og kontrollere at eksporten dekker det.
Kontrollen verifiserer ikke katalogens fullstendighet, korrekt regnskapsmessig
kontovalg eller standardens øvrige krav. Full NS 4102-kontroll i Agaas står ventende.

## Installasjon i et annet repo og CI

Installer Pixi og legg til følgende `pixi.toml`. Kjør `pixi install` én gang og
commit både manifest og `pixi.lock`. Låsefilen binder wheel-filen og øvrige
avhengigheter til kontrollsummer. CI bruker alltid `pixi install --locked`.

```toml
[workspace]
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[dependencies]
python = "3.13.*"
lxml = "6.*"

[pypi-dependencies]
agaas-saft = { url = "https://github.com/AgaasNO/saf-t-validator/releases/download/v0.1.0/agaas_saft-0.1.0-py3-none-any.whl" }
```

Applikasjonens tester kaller `pixi run --locked agaas-saft validate - --schema-version 1.40`
som en prosess med XML-bytes på stdin. Kontroller både returkode og rapportens
`interface_version`, `status` og nødvendige `checks`. Timeout, signalavbrudd,
manglende JSON eller returkode 2 skal feile testen, aldri bli tolket som en ugyldig
eksport eller en hoppet-over test. Gi installasjonen eget CI-steg, slik at
nettverksfeil holdes atskilt fra valideringsfeil.

Python-tester kan bruke samme implementasjon direkte:

```python
from agaas_saft.validation import validate_saft

report = validate_saft(xml_bytes, schema_version="1.40")
assert report.status == "valid", report.to_dict()
assert report.checks["schema"] == "passed"
```

Wheel-filen inneholder kode, to XSD-er, to kodelister og kildehenvisninger. Historikk,
eksempelfiler og tester følger ikke med. Ved oppgradering endres utgivelses-URL
og låsefil sammen i en gjennomgått endring. Ingen test laster ned «latest».
