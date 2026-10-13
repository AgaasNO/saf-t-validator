# Kilder og avgrensning

Skjemaer, kodelister og offisielle testfiler kommer fra
[Skatteetaten/saf-t, revisjon 05179521e435d82feb0b2d6c89a92a32a4f2d02f](https://github.com/Skatteetaten/saf-t/tree/05179521e435d82feb0b2d6c89a92a32a4f2d02f).
[Kildemanifestet](../src/agaas_saft/data/provenance.json) registrerer opprinnelige
filnavn og SHA-256. Filene er flyttet, men innholdet er uendret. Testene kontrollerer
disse summene. Forken beholder Git-historikken.

Utvalget omfatter XSD 1.30 og 1.40, næringsspesifikasjon 2025–2026, standard
MVA-koder og ett offisielt XML-eksempel per versjon. Kassasystem, signaturverktøy,
møtereferater, utkast til 2.0, regneark, eldre formatversjoner og ubrukte kodelister
er fjernet fra arbeidstreet. De finnes fortsatt i upstream-historikken.

[Skatteetatens dokumentasjon](https://www.skatteetaten.no/bedrift-og-organisasjon/starte-og-drive/rutiner-regnskap-og-kassasystem/saf-t-regnskap/dokumentasjon/)
angir 1.40 for regnskapsår fra 2027. Skjemakontroll kan brukes allerede nå.
Årsbestemte kodelister oppdateres separat; dette utvalget inneholder ingen liste
merket 2027. Verktøyet gir derfor feil hvis denne kontrollen etterspørres.

[Teknisk dokumentasjon, versjon 1.8](https://www.skatteetaten.no/globalassets/bedrift-og-organisasjon/starte-og-drive/rutiner-regnskap-og-kassasystem/saf-t-regnskap/august2026/norwegian-saf-t-financial-data---documentation-1.40.pdf)
beskriver kontokobling til næringsspesifikasjonen og unntaksverdien `NA` i avsnittene
om MVA-koder og kontokobling. Kontroll av medlemskap i listene avgjør ikke om
valgt kode eller unntak er regnskapsmessig riktig.

NS 4102 er en separat kontoplanstandard. [Standard Norge](https://standard.no/fagomrader/kontoplan-for-regnskap/)
beskriver 2023-utgaven og muligheten for fire- eller femsifrede kontoer. Ingen
lisensiert kontoplan er inkludert. Upstreams gamle General Ledger Standard Accounts
inngår heller ikke; disse listene er ikke NS 4102:2023 og har egne bruksvilkår.
Upstreams opprinnelige tekst er bevart i [UPSTREAM-README.md](../UPSTREAM-README.md).

Følgende ligger utenfor denne validatoren: journalbalanse, summer og antall,
referanser mellom poster, fullstendighet mot hovedbok, perioderegler, MVA-behandling,
bilagsdokumentasjon og full kontroll mot NS 4102. Agaas må ha egne akseptansetester
for disse egenskapene. En bestått formatkontroll er ikke en samsvarserklæring.

Ved kildeoppdatering velges en bestemt upstream-revisjon. Oppdater bare aktuelle
filer og manifestet, kjør testene mot begge versjoner, og publiser en ny utgivelse.
Utgitte pakker og versjonstagger skal ikke overskrives.
