# Innflytting av eldre regnskap

Anbefalingen er at Agaas etter hvert kan importere eldre SAF-T-versjoner direkte til sin interne regnskapsmodell, og eksportere derfra som 1.40. Kunden bør levere eksporten fra sitt eksisterende system. Vi bør ikke basere innflytting på at kunden selv utvikler eller kjøper en konverterer. Dette er en produktanbefaling, ikke et SAF-T-krav. Validering krever ingen konverterer, så vi trenger ikke bygge import eller konvertering for å ferdigstille testgrensesnittet.

Skatteetaten krever 1.40 for regnskapsperioder som begynner 1. januar 2027 eller senere. Eldre regnskap trenger ikke automatisk omskrives til 1.40. Den detaljerte dokumentasjonen tillater 1.20 for 2024 og tidligere, og krever 1.30 fra 2025. Kravet gjelder gjengivelse av bokførte opplysninger i SAF-T, og innebærer ikke et generelt krav om at Agaas skal importere alle tidligere versjoner. [Skatteetatens versjonsregler, side 9][dokumentasjon] og [beskrivelse av eksportplikten][saft].

En importør for 1.20 må håndtere reelle forskjeller. I 1.30 ble valget om mapping til standardkontoplan fjernet, `GroupingCategory` og `GroupingCode` ble obligatoriske, avgiftsbeløp ble delt i debet og kredit, og kunders og leverandørers saldoer fikk ny struktur. En endring av versjonsnummeret er derfor utilstrekkelig. Skatteetaten beskriver 1.40 som bakoverkompatibel med 1.30 på skjemanivå. Det fritar ikke en ny eksport fra korrekt versjonsangivelse og øvrige formatkrav. [Endringsoversikten, side 5 til 8][dokumentasjon].

SAF-T inneholder hovedbok, kundereskontro, leverandørreskontro og tilhørende grunndata. Formatet er ikke en full sikkerhetskopi av regnskapssystemet og inkluderer ikke bilagsvedlegg. [Formatets omfang, side 9][dokumentasjon].

Ved innflytting bør kunden eller regnskapsføreren derfor levere original eksport, manglende bilag og nødvendige kontokoblinger. Agaas bør validere kildefilen, bevare den uendret og avstemme importerte saldoer og transaksjoner før kunden godkjenner innflyttingen. NS 4102-kontoplanen må behandles separat fra konvertering mellom SAF-T-versjoner.

[dokumentasjon]: https://www.skatteetaten.no/globalassets/bedrift-og-organisasjon/starte-og-drive/rutiner-regnskap-og-kassasystem/saf-t-regnskap/august2026/norwegian-saf-t-financial-data---documentation-1.40.pdf
[saft]: https://www.skatteetaten.no/en/business-and-organisation/start-and-run/best-practices-accounting-and-cash-register-systems/saf-t-financial/
