# RRULE-Semantik

## Monatliche Regeln ohne `BYMONTHDAY`

Für `FREQ=MONTHLY` leitet Safe Start den nicht explizit angegebenen
Monatstag aus `DTSTART` ab. Eine am 15. angelegte Automation läuft damit am
15. jedes passenden Monats; ein explizites `BYMONTHDAY` hat Vorrang.

Der Catch-up-Bericht behält den ursprünglichen Erstellungszeitpunkt als
`DTSTART` bei, auch wenn er nur ein späteres Lookback-Fenster auswertet.
Nicht vorhandene Kalendertage (etwa der 31. im Februar) werden nicht auf den
Monatsletzten verschoben. WEEKLY und YEARLY bleiben von dieser Monatsregel
unberührt.
