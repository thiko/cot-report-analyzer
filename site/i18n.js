/* Interface strings, English and German.
 *
 * Values are either a plain string or a function of the interpolated values, so
 * a sentence that has to bend around a number or a name stays one entry in one
 * place rather than being assembled from fragments at the call site — German
 * and English put those parts in different orders.
 *
 * Not translated on purpose: market names, trader group labels and report
 * labels. Those are the CFTC's own terms, and German market commentary uses
 * them in English — "Managed Money", not "verwaltetes Geld".
 */

export const LANGUAGES = ["en", "de"];
export const DEFAULT_LANGUAGE = "en";

export const LANGUAGE_NAMES = { en: "English", de: "Deutsch" };

const EN = {
  "meta.locale": "en-US",
  "meta.ordinal": (n) => {
    const tens = n % 100;
    if (tens >= 11 && tens <= 13) return `${n}th`;
    return `${n}${["th", "st", "nd", "rd"][n % 10] || "th"}`;
  },

  "app.dataThrough": ({ date }) => `data through ${date}`,
  "app.theme": "Theme",
  "app.themeAria": "Switch colour theme",
  "app.languageAria": "Interface language",

  "toolbar.reportDate": "Report date",
  "toolbar.compareWith": "Compare with",
  "toolbar.category": "Category",
  "toolbar.search": "Search",
  "toolbar.searchPlaceholder": "Corn, GC, …",
  "toolbar.traderGroups": "Trader groups",
  "toolbar.netShownAs": "Net shown as",
  "toolbar.contracts": "Contracts",
  "toolbar.pctOi": "% of OI",
  "toolbar.allCategories": "All categories",
  "toolbar.compareNone": "— none —",
  "toolbar.previousWeek": "Previous week",
  "toolbar.weeksAgo": ({ n }) => `${n} weeks ago`,

  "table.caption": "Net positioning by market and trader group",
  "table.market": "Market",
  "table.openInterest": "Open Interest",
  "table.total": "Total",
  "table.deltaWeek": "Δ week",
  "table.deltaCompare": "Δ vs cmp",
  "table.net": "Net",
  "table.pctOi": "% OI",
  "table.w25": "25w",
  "table.w52": "52w",
  "table.y3": "3y",
  "table.loading": "Loading…",
  "table.noMatch": "No markets match these filters.",

  "range.25": "25w",
  "range.52": "52w",
  "range.156": "3y",
  "range.0": "Max",

  "signal.reversal": "Reversal",
  "signal.turning": "Turning",
  "signal.titleReversal": "Speculators at a 52-week extreme, the weekly flow running against it,"
    + " and hedgers at the mirror extreme.",
  "signal.titleTurning": "Speculators at a 52-week extreme with the weekly flow running against it.",

  "tier.A": "Crowded, turning, hedgers at the mirror, and open interest rising — fresh money"
    + " arriving as the extreme breaks.",
  "tier.B": "Crowded, turning, hedgers at the mirror, but open interest is flat or falling.",
  "tier.C": "Crowded and turning, without the hedgers at the matching extreme.",

  "shortlist.title": "Worth a closer look",
  "shortlist.blurb": "Every report type scanned for this week: positioning at a 52-week extreme"
    + " with the weekly flow turning against it, ranked. A shortlist for research, not advice —"
    + " the direction each card names follows from the positioning alone, no price series enters"
    + " this build.",
  "shortlist.scanning": "scanning…",
  "shortlist.count": ({ n }) => `${n} market${n === 1 ? "" : "s"}`,
  "shortlist.nothing": "nothing flagged",
  "shortlist.empty": "No market is at a positioning extreme with the weekly flow turning against"
    + " it this week.",
  "shortlist.excluded": ({ min, list }) => `Held back as too thin to read — under ${min} contracts`
    + ` of open interest: ${list}.`,

  "card.pressureLong": "Speculators crowded long — an unwind means them selling",
  "card.pressureShort": "Speculators crowded short — an unwind means them buying",
  "card.window52": ({ label }) => `${label} 52w`,
  "card.openInterest": "Open interest",
  "card.shareOfOi": "Share of OI",
  "card.concentrated": ({ pct }) => `Position is ${pct}% of open interest. Historically the`
    + " heavily concentrated ones unwound more slowly, not faster.",

  "takeaway.label": "Read as",
  "takeaway.down": ({ rate, base }) => "The crowded long probably unwinds, which means them"
    + ` selling — ${rate}% of comparable weeks did within eight weeks, against ${base}% for any`
    + " position at all. Leaning short, or standing aside from a long, is what this fits.",
  "takeaway.up": ({ rate, base }) => "The crowded short probably unwinds, which means them"
    + ` buying — ${rate}% of comparable weeks did within eight weeks, against ${base}% for any`
    + " position at all. Leaning long, or standing aside from a short, is what this fits.",
  "takeaway.building": "No unwind indicated yet — the crowd is still adding to the extreme. The"
    + " setup is only measurable once the weekly flow turns.",
  "takeaway.quiet": "Nothing indicated — positioning is unremarkable this week.",

  "summary.noPair": "No speculator/hedger pair is defined for this report, so there is nothing"
    + " to summarise beyond the columns themselves.",
  "summary.position": ({ group, direction, size, share }) =>
    `<b>${group}</b> is net <b>${direction} ${size}</b> contracts${share}.`,
  "summary.shareOfOi": ({ pct }) => `, ${pct}% of open interest`,
  "summary.long": "long",
  "summary.short": "short",
  "summary.flat": "flat",
  "summary.windows": ({ p25, p156 }) => [
    p25 === null ? null : `${p25} over 25 weeks`,
    p156 === null ? null : `${p156} over three years`,
  ].filter(Boolean).join(", "),
  "summary.percentile": ({ pct, windows, reading }) =>
    `That is the <b>${pct} percentile</b> of the last 52 weeks${windows ? ` (${windows})` : ""}`
    + ` — ${reading}. In the percentile columns blue marks the net-long end of a market's own`
    + " range and red the net-short end; only the top and bottom decile get any wash.",
  "summary.readingLong": "this crowd has rarely been more long",
  "summary.readingShort": "this crowd has rarely been more short",
  "summary.readingMid": "mid-range, nothing stretched",
  "summary.change": ({ verb, size, against }) =>
    `This week the net figure <b>${verb} ${size}</b> contracts${against}.`,
  "summary.rose": "rose",
  "summary.fell": "fell",
  "summary.againstExtreme": " — movement against the extreme, which is what the badge tracks",
  "summary.pushingFurther": " — still pushing the extreme further",
  "summary.hedger": ({ group, pct, mirror }) =>
    `<b>${group}</b> holds the <b>${pct} percentile</b>${mirror}.`,
  "summary.mirrorNote": ", the mirror image — both sides of the market sit at their limit",

  "verdict.reversalLabel": "Reversal setup",
  "verdict.reversal": " — crowded, turning, and confirmed by the hedgers. Historically the"
    + " strongest of the three buckets, and it still only unwound about six times in ten.",
  "verdict.turningLabel": "Turning",
  "verdict.turning": " — crowded with the flow going the other way, but the hedgers are not at"
    + " the matching extreme, so the weaker of the two flags.",
  "verdict.noneLabel": "No flag",
  "verdict.building": " — positioning is extreme but still building in the same direction. On its"
    + " own an extreme says little; it persists for a median of three weeks and has run as long"
    + " as 94.",
  "verdict.quiet": " — positioning is nowhere near an extreme this week.",

  "detail.netHistory": ({ name }) => `${name} — net position history`,
  "detail.longShortSplit": "Long / short split",
  "detail.termStructure": "Term structure",
  "detail.noData": "no data",
  "detail.noCurve": "No settlement curve stored for this market.",
  "detail.long": "Long",
  "detail.short": "Short",
  "detail.spread": "Spread",
  "detail.settlement": "Settlement",
  "detail.detailsFor": ({ name }) => `Details for ${name}`,
  "detail.infoFor": ({ name }) => `What the numbers say about ${name}`,

  "notes.readingTitle": "Reading the table",
  "notes.reading1": "<strong>Net</strong> is long minus short positions for that trader group."
    + " Positive means net long.",
  "notes.reading2": "<strong>Δ week</strong> is the change the CFTC reports against the prior week.",
  "notes.reading3": "<strong>25w / 52w / 3y</strong> are percentile ranks of the current net"
    + " position within that trailing window. 90 means the position has been more long than this"
    + " in only 10% of the weeks.",
  "notes.reading4": "Blue marks the net-long end of a market's own range, red the net-short end."
    + " Only the top and bottom decile are shaded, deeper past the 95th and 5th; everything"
    + " between stays plain. The number always carries the value, colour only repeats it.",
  "notes.reading5": "The <strong>&#x24d8;</strong> on each row spells the current week out in"
    + " words — what the position is, how stretched, which way it moved and whether anything is"
    + " flagged. Hover it, or click to pin it open.",

  "notes.flagsTitle": "The two flags",
  "notes.flags1": "<strong>Reversal</strong> — speculators sit in the top or bottom decile of"
    + " their 52-week range, the weekly change runs <em>against</em> that extreme, and hedgers"
    + " hold the mirror extreme on the other side. Roughly 5% of market-weeks.",
  "notes.flags2": "<strong>Turning</strong> — the same extreme and the same counter-flow, but"
    + " without the hedger confirmation. Roughly 9% of market-weeks.",
  "notes.flags3": "Measured over the committed 2022–2026 history, eight weeks forward, in units"
    + " of each market's own 52-week deviation: an extreme percentile on its own unwound 59% of"
    + " the time, adding the turn 61%, adding the hedger mirror 62%. Useful as a shortlist, not"
    + " as a trigger.",
  "notes.flags4": "An extreme percentile alone is <em>not</em> flagged. It occurs in nearly 40%"
    + " of market-weeks and persists for a median of three, because a trending position sits at"
    + " the edge of its own window by construction.",

  "notes.flags5": "<strong>Read as</strong> closes every card and every <strong>&#x24d8;</strong>"
    + " box with the thing the forward test actually measured — whether the position unwinds —"
    + " and the flow that implies. It stops there on purpose: no price series enters this build,"
    + " so whether the market follows the flow is untested here.",
  "notes.flags6": ({ base }) => "Every rate is quoted against its base rate: any liquid position"
    + ` away from its own median unwound ${base}% of the time over the same eight weeks. A 64%`
    + " bucket is that much better than doing nothing, not 64% right.",

  "notes.whoTitle": "Who is who",
  "notes.sourceTitle": "Source",
  "notes.source1": "CFTC Commitments of Traders, published Fridays at 15:30 ET for the preceding"
    + " Tuesday.",
  "notes.source2": "Every report type is rebuilt weekly and committed to the repository, so any"
    + " past week stays reachable through the date picker.",
  "notes.curvesAvailable": "Term structure curves come from CME settlement data stored alongside"
    + " the positions.",
  "notes.curvesMissing": "Term structure curves are unavailable — CME Group blocks automated"
    + " access to its settlement endpoint.",

  "glossary.producer": "Physical hedgers — they own or need the commodity and sell into strength.",
  "glossary.swap": "Swap dealers hedging over-the-counter exposure, largely index-related flow.",
  "glossary.managed_money": "CTAs and hedge funds. Trend followers, and the crowd that gets squeezed.",
  "glossary.other_reportable": "Large traders that fit no other bucket.",
  "glossary.nonreportable": "Everyone below the reporting threshold — small speculators.",
  "glossary.commercial": "Hedgers with a business in the underlying market.",
  "glossary.noncommercial": "Large speculators without a commercial hedging need.",
  "glossary.index_trader": "Commodity index funds tracking a long-only benchmark.",
  "glossary.dealer": "Sell-side intermediaries. Their book is the mirror of client flow.",
  "glossary.asset_manager": "Pensions, insurers and mutual funds holding long-term exposure.",
  "glossary.leveraged_money": "Hedge funds and levered accounts — the fast money in financials.",
  "glossary.gap": "Speculators minus hedgers. Extremes flag crowded, one-sided positioning.",
};

const DE = {
  "meta.locale": "de-DE",
  "meta.ordinal": (n) => `${n}.`,

  "app.dataThrough": ({ date }) => `Daten bis ${date}`,
  "app.theme": "Design",
  "app.themeAria": "Farbschema wechseln",
  "app.languageAria": "Sprache der Oberfläche",

  "toolbar.reportDate": "Berichtsdatum",
  "toolbar.compareWith": "Vergleichen mit",
  "toolbar.category": "Kategorie",
  "toolbar.search": "Suche",
  "toolbar.searchPlaceholder": "Corn, GC, …",
  "toolbar.traderGroups": "Händlergruppen",
  "toolbar.netShownAs": "Netto anzeigen als",
  "toolbar.contracts": "Kontrakte",
  "toolbar.pctOi": "% des OI",
  "toolbar.allCategories": "Alle Kategorien",
  "toolbar.compareNone": "— keiner —",
  "toolbar.previousWeek": "Vorwoche",
  "toolbar.weeksAgo": ({ n }) => `vor ${n} Wochen`,

  "table.caption": "Nettopositionierung nach Markt und Händlergruppe",
  "table.market": "Markt",
  "table.openInterest": "Open Interest",
  "table.total": "Gesamt",
  "table.deltaWeek": "Δ Woche",
  "table.deltaCompare": "Δ zum Vgl.",
  "table.net": "Netto",
  "table.pctOi": "% OI",
  "table.w25": "25W",
  "table.w52": "52W",
  "table.y3": "3J",
  "table.loading": "Wird geladen…",
  "table.noMatch": "Keine Märkte passen zu diesen Filtern.",

  "range.25": "25W",
  "range.52": "52W",
  "range.156": "3J",
  "range.0": "Max",

  "signal.reversal": "Umkehr",
  "signal.turning": "Dreht",
  "signal.titleReversal": "Spekulanten am 52-Wochen-Extrem, der Wochenfluss läuft dagegen, und"
    + " die Hedger stehen am Spiegelextrem.",
  "signal.titleTurning": "Spekulanten am 52-Wochen-Extrem, der Wochenfluss läuft dagegen.",

  "tier.A": "Überfüllt, dreht, Hedger am Spiegelextrem, und das Open Interest steigt — frisches"
    + " Geld kommt herein, während das Extrem bricht.",
  "tier.B": "Überfüllt, dreht, Hedger am Spiegelextrem, aber das Open Interest ist flach oder"
    + " fällt.",
  "tier.C": "Überfüllt und drehend, ohne Hedger am passenden Gegenextrem.",

  "shortlist.title": "Genauer ansehen",
  "shortlist.blurb": "Alle Reporttypen für diese Woche gescannt: Positionierung am"
    + " 52-Wochen-Extrem, bei der der Wochenfluss dagegen dreht, sortiert. Eine Vorauswahl zum"
    + " Recherchieren, keine Anlageberatung — die Richtung, die jede Kachel nennt, folgt allein"
    + " aus der Positionierung, in diesen Build fließt keine Preisreihe ein.",
  "shortlist.scanning": "wird gescannt…",
  "shortlist.count": ({ n }) => `${n} ${n === 1 ? "Markt" : "Märkte"}`,
  "shortlist.nothing": "nichts markiert",
  "shortlist.empty": "Diese Woche steht kein Markt an einem Positionierungsextrem, bei dem der"
    + " Wochenfluss dagegen dreht.",
  "shortlist.excluded": ({ min, list }) => `Zurückgehalten, weil zu dünn — unter ${min} Kontrakten`
    + ` Open Interest: ${list}.`,

  "card.pressureLong": "Spekulanten überfüllt long — ein Abbau bedeutet, dass sie verkaufen",
  "card.pressureShort": "Spekulanten überfüllt short — ein Abbau bedeutet, dass sie kaufen",
  "card.window52": ({ label }) => `${label} 52W`,
  "card.openInterest": "Open Interest",
  "card.shareOfOi": "Anteil am OI",
  "card.concentrated": ({ pct }) => `Position entspricht ${pct}% des Open Interest. Historisch`
    + " bauten sich die stark konzentrierten langsamer ab, nicht schneller.",

  "takeaway.label": "Ablesen",
  "takeaway.down": ({ rate, base }) => "Der überfüllte Long baut sich wahrscheinlich ab, das heißt"
    + ` Verkaufsdruck — ${rate}% der vergleichbaren Wochen taten das binnen acht Wochen, gegen`
    + ` ${base}% für eine beliebige Position. Dazu passt eher die Short-Seite oder Zurückhaltung`
    + " beim Long-Einstieg.",
  "takeaway.up": ({ rate, base }) => "Der überfüllte Short baut sich wahrscheinlich ab, das heißt"
    + ` Kaufdruck — ${rate}% der vergleichbaren Wochen taten das binnen acht Wochen, gegen`
    + ` ${base}% für eine beliebige Position. Dazu passt eher die Long-Seite oder Zurückhaltung`
    + " beim Short-Einstieg.",
  "takeaway.building": "Noch kein Abbau angezeigt — die Menge baut das Extrem weiter aus. Messbar"
    + " wird die Konstellation erst, wenn der Wochenfluss dreht.",
  "takeaway.quiet": "Nichts angezeigt — die Positionierung ist diese Woche unauffällig.",

  "summary.noPair": "Für diesen Report ist kein Spekulanten/Hedger-Paar definiert, es gibt also"
    + " über die Spalten hinaus nichts zusammenzufassen.",
  "summary.position": ({ group, direction, size, share }) =>
    `<b>${group}</b> ist netto <b>${direction} ${size}</b> Kontrakte${share}.`,
  "summary.shareOfOi": ({ pct }) => `, ${pct}% des Open Interest`,
  "summary.long": "long",
  "summary.short": "short",
  "summary.flat": "flat",
  "summary.windows": ({ p25, p156 }) => [
    p25 === null ? null : `${p25} über 25 Wochen`,
    p156 === null ? null : `${p156} über drei Jahre`,
  ].filter(Boolean).join(", "),
  "summary.percentile": ({ pct, windows, reading }) =>
    `Das ist das <b>${pct} Perzentil</b> der letzten 52 Wochen${windows ? ` (${windows})` : ""}`
    + ` — ${reading}. In den Perzentilspalten steht Blau für das Long-Ende der markteigenen`
    + " Spanne und Rot für das Short-Ende; eingefärbt wird nur das oberste und unterste Dezil.",
  "summary.readingLong": "selten war diese Gruppe stärker long",
  "summary.readingShort": "selten war diese Gruppe stärker short",
  "summary.readingMid": "Mittelfeld, nichts überdehnt",
  "summary.change": ({ verb, size, against }) =>
    `Diese Woche ${verb} der Nettowert um <b>${size}</b> Kontrakte${against}.`,
  "summary.rose": "stieg",
  "summary.fell": "fiel",
  "summary.againstExtreme": " — Bewegung gegen das Extrem, und genau darauf achtet der Marker",
  "summary.pushingFurther": " — das Extrem wird weiter ausgebaut",
  "summary.hedger": ({ group, pct, mirror }) =>
    `<b>${group}</b> steht im <b>${pct} Perzentil</b>${mirror}.`,
  "summary.mirrorNote": " — das Spiegelbild, beide Marktseiten stehen an ihrer Grenze",

  "verdict.reversalLabel": "Umkehr-Konstellation",
  "verdict.reversal": " — überfüllt, drehend und von den Hedgern bestätigt. Historisch der"
    + " stärkste der drei Buckets, und trotzdem löste er sich nur in etwa sechs von zehn Fällen"
    + " auf.",
  "verdict.turningLabel": "Dreht",
  "verdict.turning": " — überfüllt bei gegenläufigem Fluss, aber die Hedger stehen nicht am"
    + " passenden Gegenextrem, also der schwächere der beiden Marker.",
  "verdict.noneLabel": "Kein Marker",
  "verdict.building": " — die Positionierung ist extrem, wird aber weiter in dieselbe Richtung"
    + " ausgebaut. Für sich genommen sagt ein Extrem wenig; es hält im Median drei Wochen und lief"
    + " schon 94 Wochen am Stück.",
  "verdict.quiet": " — die Positionierung ist diese Woche weit von einem Extrem entfernt.",

  "detail.netHistory": ({ name }) => `${name} — Verlauf der Nettoposition`,
  "detail.longShortSplit": "Long/Short-Aufteilung",
  "detail.termStructure": "Terminkurve",
  "detail.noData": "keine Daten",
  "detail.noCurve": "Für diesen Markt ist keine Settlement-Kurve gespeichert.",
  "detail.long": "Long",
  "detail.short": "Short",
  "detail.spread": "Spread",
  "detail.settlement": "Settlement",
  "detail.detailsFor": ({ name }) => `Details zu ${name}`,
  "detail.infoFor": ({ name }) => `Was die Zahlen zu ${name} sagen`,

  "notes.readingTitle": "Die Tabelle lesen",
  "notes.reading1": "<strong>Netto</strong> ist Long minus Short für diese Händlergruppe."
    + " Positiv heißt netto long.",
  "notes.reading2": "<strong>Δ Woche</strong> ist die Veränderung, die die CFTC gegenüber der"
    + " Vorwoche ausweist.",
  "notes.reading3": "<strong>25W / 52W / 3J</strong> sind Perzentilränge der aktuellen"
    + " Nettoposition innerhalb dieses rückwärtigen Fensters. 90 heißt, die Position war nur in"
    + " 10% der Wochen stärker long.",
  "notes.reading4": "Blau markiert das Long-Ende der markteigenen Spanne, Rot das Short-Ende."
    + " Eingefärbt wird nur das oberste und unterste Dezil, kräftiger jenseits des 95. und 5.;"
    + " alles dazwischen bleibt schlicht. Die Zahl trägt immer den Wert, die Farbe wiederholt ihn"
    + " nur.",
  "notes.reading5": "Das <strong>&#x24d8;</strong> in jeder Zeile schreibt die aktuelle Woche in"
    + " Worten aus — wie die Position steht, wie überdehnt, in welche Richtung sie sich bewegt hat"
    + " und ob etwas markiert ist. Mit der Maus darüber, oder klicken zum Feststellen.",

  "notes.flagsTitle": "Die zwei Marker",
  "notes.flags1": "<strong>Umkehr</strong> — die Spekulanten stehen im obersten oder untersten"
    + " Dezil ihrer 52-Wochen-Spanne, die Wochenveränderung läuft <em>gegen</em> dieses Extrem,"
    + " und die Hedger halten das Spiegelextrem auf der Gegenseite. Rund 5% der Marktwochen.",
  "notes.flags2": "<strong>Dreht</strong> — dasselbe Extrem und derselbe Gegenfluss, aber ohne"
    + " Bestätigung durch die Hedger. Rund 9% der Marktwochen.",
  "notes.flags3": "Gemessen über die eingecheckte Historie 2022–2026, acht Wochen voraus, in"
    + " Einheiten der markteigenen 52-Wochen-Abweichung: ein Perzentil-Extrem für sich löste sich"
    + " in 59% der Fälle auf, mit dem Dreher 61%, mit dem Hedger-Spiegel 62%. Taugt als"
    + " Vorauswahl, nicht als Auslöser.",
  "notes.flags4": "Ein Perzentil-Extrem allein wird <em>nicht</em> markiert. Es tritt in fast 40%"
    + " der Marktwochen auf und hält im Median drei Wochen, weil eine trendende Position"
    + " zwangsläufig am Rand ihres eigenen Fensters klebt.",

  "notes.flags5": "<strong>Ablesen</strong> schließt jede Kachel und jede"
    + " <strong>&#x24d8;</strong>-Box mit dem ab, was der Forward-Test tatsächlich gemessen hat —"
    + " ob sich die Position auflöst — und mit dem Fluss, der daraus folgt. Bewusst nicht weiter:"
    + " in diesen Build fließt keine Preisreihe ein, ob der Markt dem Fluss folgt, ist hier"
    + " ungeprüft.",
  "notes.flags6": ({ base }) => "Jede Quote steht gegen ihre Basisrate: eine beliebige liquide"
    + ` Position abseits ihres eigenen Medians löste sich über dieselben acht Wochen in ${base}%`
    + " der Fälle auf. Ein 64%-Bucket ist um diesen Abstand besser als Nichtstun, nicht zu 64%"
    + " richtig.",

  "notes.whoTitle": "Wer ist wer",
  "notes.sourceTitle": "Quelle",
  "notes.source1": "CFTC Commitments of Traders, veröffentlicht freitags um 15:30 ET für den"
    + " vorangegangenen Dienstag.",
  "notes.source2": "Jeder Reporttyp wird wöchentlich neu gebaut und ins Repository eingecheckt,"
    + " jede vergangene Woche bleibt also über die Datumsauswahl erreichbar.",
  "notes.curvesAvailable": "Die Terminkurven stammen aus CME-Settlement-Daten, die neben den"
    + " Positionen gespeichert werden.",
  "notes.curvesMissing": "Terminkurven sind nicht verfügbar — CME Group blockiert den"
    + " automatisierten Zugriff auf den Settlement-Endpunkt.",

  "glossary.producer": "Physische Hedger — sie besitzen den Rohstoff oder brauchen ihn und"
    + " verkaufen in die Stärke hinein.",
  "glossary.swap": "Swap Dealer, die außerbörsliches Exposure absichern, überwiegend"
    + " indexgetriebener Fluss.",
  "glossary.managed_money": "CTAs und Hedgefonds. Trendfolger, und die Menge, die gequetscht wird.",
  "glossary.other_reportable": "Große Händler, die in keine andere Kategorie passen.",
  "glossary.nonreportable": "Alle unterhalb der Meldeschwelle — Kleinspekulanten.",
  "glossary.commercial": "Hedger mit einem Geschäft im zugrunde liegenden Markt.",
  "glossary.noncommercial": "Große Spekulanten ohne kommerziellen Absicherungsbedarf.",
  "glossary.index_trader": "Rohstoffindexfonds, die eine reine Long-Benchmark abbilden.",
  "glossary.dealer": "Intermediäre der Sell Side. Ihr Buch ist das Spiegelbild des Kundenflusses.",
  "glossary.asset_manager": "Pensionskassen, Versicherer und Fonds mit langfristigem Exposure.",
  "glossary.leveraged_money": "Hedgefonds und gehebelte Konten — das schnelle Geld in den"
    + " Finanzmärkten.",
  "glossary.gap": "Spekulanten minus Hedger. Extreme zeigen überfüllte, einseitige"
    + " Positionierung an.",
};

export const STRINGS = { en: EN, de: DE };
