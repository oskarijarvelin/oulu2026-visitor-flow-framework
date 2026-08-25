/**
 * Suomenkieliset tekstit. Tama tiedosto on kaannosten lahde: `en.ts` tyypitetaan tata
 * vasten, joten puuttuva tai vaaran muotoinen avain kaataa tyyppitarkistuksen.
 *
 * Tekstit ovat funktioita silloin kun niissa on lukuja tai paivamaaria, jotta
 * sanajarjestys voi vaihdella kielten valilla.
 */

export const fi = {
  site: {
    name: 'Oulu2026 kävijävirrat',
    titleSuffix: 'Oulu2026 kävijävirrat',
    updatedAt: (when: string) => `Päivitetty ${when}`,
    skipToContent: 'Siirry sisältöön',
    footerUnit:
      'Kaikki luvut ovat kävijätapahtumia: visitors_total on sisään- ja ulosmenojen summa, ei uniikkien kävijöiden määrä. Ajat ovat Suomen aikaa.',
    footerRuns: (ingest: string, forecast: string) =>
      `Aineisto haettu ${ingest}, ennuste ajettu ${forecast}. Sivusto on staattinen ja rakennetaan uudelleen jokaisella ajolla.`,
    footerAboutLink: 'Mistä data tulee',
  },

  nav: {
    label: 'Päävalikko',
    overview: 'Yleiskuva',
    weather: 'Sää',
    forecast: 'Ennuste',
    quality: 'Laatu',
    accuracy: 'Tarkkuus',
    about: 'Tietoja',
    languageLabel: 'Kieli',
    switchTo: (language: string) => `Vaihda kieleksi ${language}`,
    currentLanguage: (language: string) => `Nykyinen kieli: ${language}`,
  },

  banner: {
    region: 'Datan laatu',
    ok: 'Data on ajan tasalla',
    issues: 'Datan laadussa huomautettavaa',
    fetched: (when: string, hours: string) => `Viimeisin haku ${when}, ${hours} tuntia sitten.`,
    coverage: (last: string) => `Havainnot ulottuvat ${last} asti.`,
    source: (name: string, status: string) => `Lähde ${name}: ${status}`,
    forecastPrefix: 'Ennuste:',
    skippedModels: (models: string) => `Ohitetut mallit: ${models}.`,
  },

  common: {
    textAlternative: 'Tekstivastine ja taulukko',
    day: 'Päivä',
    venue: 'Venue',
    model: 'Malli',
    horizon: 'Horisontti',
    observations: 'Havaintoja',
    /** Havaintomaara luvun kanssa: "12 havaintoa", ei "12 havaintoja". */
    observationCount: (count: string) => `${count} havaintoa`,
    days: 'Vuorokausia',
    mean: 'Keskiarvo',
    median: 'Mediaani',
    largest: 'Suurin',
    hour: 'Tunti',
    visitorEvents: 'Kävijätapahtumat',
    /** Yksikko luvun perassa: partitiivi, ei nominatiivi. */
    countUnit: 'kävijätapahtumaa',
    temperature: 'Lämpötila',
    precipitation: 'Sade',
    weather: 'Säätila',
    notes: 'Huomiot',
    holiday: 'pyhä',
    rain: 'sadetta',
    partialDay: 'vajaa vuorokausi',
    forecastRow: 'ennuste',
    climatologyRow: 'sää klimatologiasta',
    entries: 'Sisään',
    exits: 'Ulos',
    production: 'tuotanto',
  },

  home: {
    title: 'Yleiskuva',
    heading: 'Kävijävirrat yhdellä silmäyksellä',
    description:
      'Oulu2026: kahden venuen kävijämäärät, sää, liput ja seitsemän vuorokauden ennuste.',
    lead: (historyDays: number, forecastDays: number, from: string, to: string) =>
      `Molempien venueiden viimeiset ${historyDays} vuorokautta ja seuraavat ${forecastDays} vuorokautta rinnakkain. Havainnot alkavat ${from} ja ulottuvat ${to} asti.`,
    keyFigures: 'Avainluvut',
    keyFiguresNote:
      'Kaikki luvut ovat kävijätapahtumia: sisään- ja ulosmenojen summa, ei uniikkeja kävijöitä. Yksi käynti tuottaa tyypillisesti kaksi tapahtumaa.',
    last30Total: 'Viimeiset 30 vrk, yhteensä',
    last30TotalNote: 'Molemmat venuet yhteensä.',
    venueMean: (venue: string) => `${venue}, 30 vrk keskiarvo`,
    perDay: '/ vrk',
    changeNote: (peakDate: string, peak: string) =>
      `Vertailu edeltäviin 30 vuorokauteen. Huippupäivä ${peakDate}: ${peak}.`,
    next7: 'Ennuste, seuraavat 7 vrk',
    next7Note: (model: string) =>
      `Mediaani, ${model}. Epävarmuusväli näkyy kaavioissa alla.`,
    panelTitle: (venue: string, historyDays: number, forecastDays: number) =>
      `${venue}: viimeiset ${historyDays} vrk ja seuraavat ${forecastDays} vrk`,
    panelDescription: (model: string, mm: string) =>
      `Yhtenäinen viiva on toteuma, katkoviiva on mediaaniennuste mallilla ${model} ja vaalea alue sen p10 - p90 -väli. Sinertävä tausta merkitsee vuorokauden jossa satoi vähintään ${mm} mm.`,
    panelFootnote: (capacity: string, hours: string) =>
      `Kapasiteetti ${capacity} henkilöä. Aukiolo aineiston perusteella klo ${hours}.`,
    panelAria: (venue: string, historyDays: number, forecastDays: number) =>
      `Aikasarja: ${venue}, kävijätapahtumat vuorokaudessa viimeiset ${historyDays} vuorokautta ja ennuste seuraavat ${forecastDays} vuorokautta.`,
    panelAlternative: (from: string, to: string, total: string, mean: string, next7: string) =>
      `Jaksolla ${from} - ${to} kertyi ${total}, keskimäärin ${mean} vuorokaudessa. Ennuste seuraaville seitsemälle vuorokaudelle on ${next7} mediaanina.`,
    tableCaption: (venue: string) => `${venue}: toteuma ja ennuste vuorokausittain`,
    actual: 'Toteuma',
    forecastP50: 'Ennuste p50',
    interval: 'p10 - p90',
    freshness: 'Datan tuoreus',
    noMissingHours: 'Ei puuttuvia tunteja.',
    missingHours: (count: string) => `${count} puuttuvaa tuntia.`,
    staleTitle: 'Ennuste lähtee vanhentuneesta tasosta',
    staleBody: (lastDay: string, runDate: string, lagDays: number) =>
      `Viimeisin havaittu vuorokausi on ${lastDay}, kun taas ennuste ajettiin ${runDate}, eli ${lagDays} vuorokautta myöhemmin. Ennuste alkaa havaintojen lopusta, ei tästä päivästä. Sama varoitus on kirjattu ennusteen manifestiin.`,
    freshTitle: 'Ennuste alkaa havaintojen lopusta',
    freshBody: (runDate: string, lastDay: string) =>
      `Ennuste ajettiin ${runDate} ja se lähtee vuorokaudesta ${lastDay}, joka on viimeisin havaittu vuorokausi. Havainnot ja ennuste ovat siis samassa tahdissa.`,
    contextHeading: 'Kontekstidata: kaupungin liikennelaskuri',
    contextBody: (site: string) =>
      `Oulun liikenteen laskuripiste ${site} on yksi mittauspiste kaupungissa. Se ei liity kumpaankaan venueen eikä sitä yhdistetä venuekohtaiseksi kävijämittariksi. Se on mukana vain taustatietona kaupungin liikkumisesta.`,
    contextNumbers: (from: string, to: string, pedestrians: string, cyclists: string) =>
      `Jaksolla ${from} - ${to} laskuri kirjasi ${pedestrians} jalankulkijaa ja ${cyclists} pyöräilijää.`,
    contextLink: 'Lisää sääsivulla',
  },

  venue: {
    description: (venue: string) =>
      `${venue}: kävijätapahtumat tunti- ja päivätasolla, viikonpäiväprofiili, kapasiteetti ja lippuvertailu.`,
    lead: (from: string, to: string, days: string, capacity: string) =>
      `Sensori raportoi ${from} alkaen. Aineisto ulottuu ${to} asti, eli ${days} raportoivaa vuorokautta. Kapasiteetti ${capacity} henkilöä.`,
    wholePeriod: 'Koko jakso',
    wholePeriodNote: (entries: string, exits: string) => `Sisään ${entries}, ulos ${exits}.`,
    dailyMean: 'Vuorokauden keskiarvo',
    dailyMeanNote: (median: string) =>
      `Mediaani ${median}. Vaihtelu on suurta, joten mediaani kuvaa tavallista päivää paremmin.`,
    last30: 'Viimeiset 30 vrk',
    last30Note: 'Vertailu edeltäviin 30 vuorokauteen.',
    busiestHour: 'Vilkkain tunti',
    busiestHourNote: (hours: string) => `Aukiolo aineiston perusteella klo ${hours}.`,

    dailyTitle: 'Kävijätapahtumat vuorokausittain',
    dailyDescription: (model: string, mm: string) =>
      `Yhtenäinen viiva on toteuma, katkoviiva mediaaniennuste ja vaalea alue sen p10 - p90 -väli. Ennusteen malli on ${model}. Sinertävä tausta merkitsee vuorokautta jossa satoi vähintään ${mm} mm, pystykatkoviiva pyhäpäivää.`,
    dailyFootnote:
      'Rajausvalitsin muuttaa näkyvää jaksoa. Ennuste alkaa aina havaintojen lopusta.',
    dailyAria: (venue: string) =>
      `Aikasarja: ${venue}, kävijätapahtumat vuorokaudessa sekä 30 vuorokauden ennuste.`,
    dailyAlternative: (
      from: string,
      to: string,
      total: string,
      mean: string,
      median: string,
      peakDate: string,
      peak: string,
      rainyDays: string,
      holidays: string,
    ) =>
      `Jaksolla ${from} - ${to} kertyi ${total}, keskimäärin ${mean} vuorokaudessa ja mediaanina ${median}. Vilkkain vuorokausi oli ${peakDate}, ${peak}. Sadepäiviä jaksolla oli ${rainyDays} ja pyhäpäiviä ${holidays}.`,
    dailyTableCaption: (venue: string) => `${venue}: viimeiset 30 havaittua vuorokautta`,

    hourlyTitle: 'Kävijätapahtumat tunneittain',
    hourlyDescription: (days: string, from: string) =>
      `Tuntisarja kattaa viimeiset ${days} vuorokautta, ${from} alkaen. Sinertävä tausta merkitsee tuntia jolla satoi vähintään 0,1 mm.`,
    hourlyFootnote:
      'Yöllä ja aukioloaikojen ulkopuolella luvut ovat aitoja nollia, eivät puuttuvaa dataa.',
    hourlyAria: (venue: string, days: number) =>
      `Aikasarja: ${venue}, kävijätapahtumat tunneittain viimeiset ${days} vuorokautta.`,
    hourlyAlternative: (hours: string, from: string, to: string, peak: string, rainHours: string, rainShare: string) =>
      `Tuntisarjassa on ${hours} tuntia ajalta ${from} - ${to}. Vilkkain yksittäinen tunti koko havaintojaksolla oli ${peak}. Sadetunteja ikkunassa on ${rainHours}, eli ${rainShare} prosenttia. Tuntikohtaiset keskiarvot löytyvät viikonpäiväprofiilin taulukosta alta.`,

    heatmapTitle: 'Viikonpäivä ja tunti',
    heatmapDescription: (from: string, to: string, days: string) =>
      `Keskimääräiset kävijätapahtumat viikonpäivän ja tunnin mukaan koko raportoivalta jaksolta ${from} - ${to}, ${days} vuorokautta.`,
    heatmapFootnote:
      'Kartta vierii vaakasuunnassa kapealla näytöllä. Ruutu jossa ei ole yhtään havaintoa on harmaa ja merkitty ristillä, aito nolla on skaalan vaalein sävy.',
    heatmapAria: (venue: string) =>
      `Lämpökartta: ${venue}, keskimääräiset kävijätapahtumat viikonpäivän ja tunnin mukaan.`,
    heatmapAlternative: (best: string) => `Vilkkain ruutu on ${best}. Taulukossa on kaikki 168 ruutua.`,
    heatmapBest: (weekday: string, hour: string, value: string) =>
      `${weekday} klo ${hour}, keskimäärin ${value} kävijätapahtumaa tunnissa`,
    heatmapNoData: 'ei havaintoja',
    heatmapTableCaption: (venue: string) => `${venue}: keskiarvo viikonpäivän ja tunnin mukaan`,

    capacityTitle: 'Sisääntulot suhteessa kapasiteettiin',
    capacityDescription: (days: number, capacity: string) =>
      `Tunnin sisääntulot aukiolotunneittain viimeisiltä ${days} vuorokaudelta. Katkoviiva on kapasiteetti ${capacity} henkilöä.`,
    capacityFootnote:
      'Tämä ei ole yhtäaikainen kävijämäärä. Viipymää ei mitata, joten sisääntulojen määrä tunnissa ei kerro kuinka moni oli paikalla samanaikaisesti. Luku kertoo kuormituksen tahdin, ei täyttöasteen.',
    capacityAria: (venue: string) =>
      `Viivakaavio: ${venue}, tunnin sisääntulot suhteessa kapasiteettiin.`,
    capacityAlternative: (peak: string, over: string, observed: string, share: string) =>
      `Vilkkaimman tunnin sisääntulojen huippu jaksolla oli ${peak}. Kapasiteetti ylittyi ${over} tunnissa ${observed} havaitusta tunnista, eli ${share} prosentissa.`,
    capacityTableCaption: (venue: string) => `${venue}: sisääntulot tunneittain`,
    capacityMean: 'Keskiarvo',
    capacityP95: '95. persentiili',
    capacityUnit: 'sisääntuloa tunnissa',
    capacityReference: (capacity: string) => `Kapasiteetti ${capacity}`,
    capacityAxis: 'Tunti, Suomen aikaa →',

    ticketsTitle: 'Lippuvertailu',
    ticketsDescription: (days: string, from: string, to: string) =>
      `Myydyt liput ja kävijätapahtumat samalta jaksolta. Lippudata on ylläpidetty käsin, ja se kattaa ${days} vuorokautta ajalta ${from} - ${to}.`,
    ticketsFootnote:
      'Kaaviot on piirretty erikseen, koska suuruusluokat eroavat. Lippu ei ole sama asia kuin kävijätapahtuma: yksi lippu voi tuottaa useita tapahtumia, ja ryhmäliput kattavat monta henkilöä.',
    ticketsVisitorsHeading: 'Kävijätapahtumat',
    ticketsSoldHeading: 'Myydyt liput',
    ticketsVisitorsAria: (venue: string) =>
      `Aikasarja: ${venue}, kävijätapahtumat vuorokausittain lippuvertailua varten.`,
    ticketsSoldAria: (venue: string) => `Aikasarja: ${venue}, myydyt liput vuorokausittain.`,
    ticketsTotal: 'Liput yhteensä',
    ticketsSingle: 'Yksittäisliput',
    ticketsGroups: 'Ryhmäliput',
    ticketsUnit: 'lippua',
    ticketsPerTicket: 'Tapahtumaa / lippu',
    ticketsNotComputable: 'ei laskettavissa',
    ticketsRatio: (ratio: string) => `${ratio} kävijätapahtumaa myytyä lippua kohti`,
    ticketsAlternative: (sold: string, events: string, ratio: string) =>
      `Jaksolla myytiin ${sold} lippua ja kirjattiin ${events}. Suhde on ${ratio}. Suhdetta ei pidä lukea kävijämääränä: osa kävijöistä tulee ilman lippua, ryhmälippu kattaa useita henkilöitä, ja jokainen käynti tuottaa sekä sisään- että ulosmenon.`,
    ticketsTableCaption: (venue: string) =>
      `${venue}: liput ja kävijätapahtumat, viimeiset 30 lipullista vuorokautta`,
    ticketsTableLabel: (venue: string) => `${venue}: liput ja kävijätapahtumat`,

    ticketWeekdayTitle: 'Lipunmyynti viikonpäivittäin, sateiset ja poutaiset päivät',
    ticketWeekdayDescription: (rainMm: string, days: string) =>
      `Keskimääräinen lippumäärä vuorokaudessa viikonpäivän mukaan, erikseen poutaisille ja sateisille päiville. Päivä on sateinen kun sademäärä on vähintään ${rainMm} mm. Mukana ${days} vuorokautta, joilla on sekä lippu- että säähavainto.`,
    ticketWeekdayFootnote:
      'Havaintoja on viikonpäivää kohti vain kymmeniä, joten yksittäisen pylvään ero on helposti sattumaa. Lue kuvaa suuntana, älä sään vaikutuksen mittarina: kesälomakausi, pyhät ja tapahtumat osuvat samoihin päiviin kuin sää, eikä tämä erottele niitä toisistaan.',
    ticketWeekdayAria: (venue: string) =>
      `Ryhmitelty pylväskaavio: ${venue}, keskimääräinen lippumäärä viikonpäivittäin, poutaiset ja sateiset päivät vierekkäin.`,
    ticketWeekdayDry: 'Poutaa',
    ticketWeekdayRainy: 'Sadetta',
    ticketWeekdayMeanColumn: 'Keskiarvo',
    ticketWeekdayMedianColumn: 'Mediaani',
    ticketWeekdayDaysColumn: 'Päiviä',
    ticketWeekdayDiffColumn: 'Ero',
    ticketWeekdayTooFew: (min: string) => `alle ${min} havaintoa, ei piirretä`,
    ticketWeekdayAlternative: (dry: string, rainy: string, diff: string) =>
      `Poutaisina päivinä keskiarvo on ${dry} ja sateisina ${rainy} lippua vuorokaudessa, eli ero on ${diff}. Taulukossa on sama jaottelu viikonpäivittäin.`,
    ticketWeekdayTableCaption: (venue: string) =>
      `${venue}: keskimääräinen lippumäärä viikonpäivän ja sään mukaan`,
    ticketWeekdayTableLabel: (venue: string) => `${venue}: liput viikonpäivittäin, sade ja pouta`,

    meaningTitle: 'Mitä luvut tarkoittavat',
    meaningBody1:
      'visitors_total on sisään- ja ulosmenojen summa. Yksi käynti tuottaa tyypillisesti kaksi tapahtumaa, joten luku ei ole uniikkien kävijöiden määrä eikä sitä voi puolittaa suoraan käyntimääräksi: ovella kääntyminen, henkilökunta ja useampi käynti samalla henkilöllä sekoittuvat samaan lukuun.',
    meaningBody2: (from: string) =>
      `Sensori otettiin käyttöön ${from}. Sitä edeltävät nollat on rajattu pois kaikista keskiarvoista ja profiileista, koska ne kertovat asentamattomasta laitteesta, eivät tyhjästä tilasta.`,
    compareLink: (venue: string) => `Vertaa toiseen venueen: ${venue}.`,
    contextNote: 'Kaupungin liikennelaskurin data on kontekstidataa eikä liity kumpaankaan venueen, katso',
    contextNoteLink: 'tietosivu',
  },

  weather: {
    title: 'Sää',
    heading: 'Sää ja kävijämäärät',
    description:
      'Sään ja kävijämäärien yhteisvaihtelu: hajontakuvio, sateiset ja poutaiset päivät sekä säätilaluokittainen jakauma.',
    lead: 'Sää kulkee samaa tahtia vuodenajan, ohjelmiston ja koulujen lomien kanssa. Kaikki tällä sivulla esitetty on yhteisvaihtelua, ei syysuhdetta. Neljän ja puolen kuukauden aineistosta ei voi erottaa säätä vuodenajasta.',

    scatterTitle: 'Lämpötila ja kävijätapahtumat',
    scatterDescription:
      'Yksi piste on yksi vuorokausi. Vaaka-akselilla vuorokauden keskilämpötila, pystyakselilla kävijätapahtumat. Väri ja symboli kertovat säätilaluokan, pisteen koko sademäärän.',
    scatterFootnote:
      'Katkoviiva on pienimmän neliösumman suora. Se kuvaa kahden suureen yhteisvaihtelua eikä sano mitään syysuhteesta.',
    scatterAria:
      'Hajontakuvio: vuorokauden keskilämpötila vaaka-akselilla ja kävijätapahtumat pystyakselilla, väri säätilaluokan mukaan.',
    scatterAlternative: (days: string, min: string, max: string, mm: string, rainyDays: string) =>
      `Aineistossa on ${days} vuorokautta molemmilta venueilta yhteensä. Lämpötila-akseli kattaa ${min} ja ${max} celsiusasteen välin. Sadetta oli vähintään ${mm} mm ${rainyDays} vuorokautena.`,
    scatterTableCaption: 'Kymmenen vilkkainta vuorokautta säätietoineen',

    rainyTitle: 'Sateiset ja poutaiset vuorokaudet',
    rainyDescription: (mm: string) =>
      `Vuorokauden keskimääräiset kävijätapahtumat sen mukaan satoiko vähintään ${mm} mm. Sama kynnys kuin ennustemallin piirteellä is_rainy_day.`,
    rainyFootnote:
      'Havaintomäärät ovat pieniä ja jakaumat vinoja, joten ero kahden pylvään välillä ei ole tilastollisesti vahva tulos.',
    rainyAria:
      'Pylväskaavio: keskimääräiset kävijätapahtumat sateisina ja poutaisina vuorokausina venuekohtaisesti.',
    rainyTableCaption: 'Sateiset ja poutaiset vuorokaudet',
    dryLabel: (venue: string) => `${venue}, poutaiset`,
    rainyLabel: (venue: string) => `${venue}, sateiset`,
    dryNote: (mm: string) => `Sade alle ${mm} mm`,
    rainyNote: (mm: string) => `Sade vähintään ${mm} mm`,
    group: 'Ryhmä',

    groupsTitle: 'Säätilaluokittainen jakauma',
    groupsDescription:
      'Vuorokauden keskimääräiset kävijätapahtumat WMO-säätilakoodin ryhmän mukaan. Ryhmittely on sama kuin ennustemallin weather_group -piirteellä.',
    groupsFootnote:
      'Ryhmien havaintomäärät vaihtelevat paljon. Lumipäiviä on aineistossa vain kourallinen, joten niiden keskiarvo on epävakaa.',
    groupsAria: 'Pylväskaavio: keskimääräiset kävijätapahtumat säätilaluokan mukaan venuekohtaisesti.',
    groupsTableCaption: 'Säätilaluokat',
    venueAndWeather: 'Venue ja säätila',

    trafficTitle: 'Kontekstidata: kaupungin liikennelaskuri',
    trafficDescription: (site: string) =>
      `Oulun liikenteen laskuripiste ${site}, jalankulkijat ja pyöräilijät vuorokausittain. Tämä on kaupungin liikennettä, ei kummankaan venuen kävijämäärä.`,
    trafficFootnote:
      'Laskuri on yksi mittauspiste Oulussa. Sitä ei yhdistetä venuekohtaiseksi mittariksi eikä se ole venue 2:n kävijädataa. Se on mukana vain taustatietona siitä miten sää näkyy kaupungilla liikkumisessa.',
    trafficAria: (site: string) =>
      `Aikasarja: ${site} -laskurin jalankulkijat ja pyöräilijät vuorokausittain.`,
    trafficAlternative: (from: string, to: string, pedestrians: string, cyclists: string, pedMean: string, cycMean: string) =>
      `Jaksolla ${from} - ${to} laskuri kirjasi ${pedestrians} jalankulkijaa ja ${cyclists} pyöräilijää, eli keskimäärin ${pedMean} ja ${cycMean} vuorokaudessa. Pyöräily kasvaa keväällä voimakkaasti, mikä näkyy sarjassa selvemmin kuin missään venuedatassa.`,
    pedestrians: 'Jalankulkijat',
    cyclists: 'Pyöräilijät',
    trafficUnit: 'ohitusta',

    causationTitle: 'Miksi sään vaikutusta ei voi eristää',
    causationBody:
      'Aineisto kattaa tammikuusta toukokuuhun 2026. Sinä aikana lämpötila nousee noin kahdestakymmenestä pakkasasteesta kesälämpötiloihin, ja samaan aikaan muuttuu kaikki muukin: ohjelmisto, koulujen lomat, valoisuus ja matkailukausi. Malli käyttää säätä piirteenä ja se parantaa ennustetta hieman, mutta piirretärkeys osoittaa tuulen nousevan lämpötilan ohi. Se on merkki siitä että säämuuttujat toimivat vuodenajan sijaisena, eivät mekanismina.',
  },

  forecast: {
    title: 'Ennuste',
    heading: 'Ennuste: 7 vuorokautta tunneittain, 30 vuorokautta päivittäin',
    description: 'Kävijämäärän ennuste molemmille venueille, epävarmuusväli ja mallien vertailu.',
    lead: (runAt: string, origin: string, model: string) =>
      `Ennuste on ajettu ${runAt} ja se lähtee vuorokaudesta ${origin}, joka on viimeisin havaittu vuorokausi. Oletuksena näkyy ${model}, joka on tuotantomalli. Jokainen ennuste esitetään aina epävarmuusvälin kanssa, ei yhtenä lukuna.`,
    warningTitle: 'Lue tämä ennen kuin käytät lukuja',
    warningWeather: (days: string) =>
      `Vuorokaudet 1-${days} käyttävät sääennustetta. Sen jälkeen sää on klimatologiaa eli kymmenen vuoden keskiarvo. Keskiarvosää tuottaa keskiarvokävijämäärän, joten horisontin loppupää on systemaattisesti liian tasainen. Raja on merkitty jokaiseen kaavioon.`,
    warningIntervals:
      'Ennustevälit ovat leveitä. Ne tulevat mitatusta backtest-virheestä, eivät mallin omista oletuksista, ja ne kertovat rehellisesti mitä neljän ja puolen kuukauden aineistolla voi sanoa. Tarkkaan resursointiin ne ovat liian leveät.',
    next7: (venue: string) => `${venue}, seuraavat 7 vrk`,
    next7Note: (low: string, high: string) =>
      `Väli ${low} - ${high}. Summa on vuorokausikohtaisten välien summa, joten se on leveämpi kuin jakson oma väli.`,
    dailyMean: (venue: string) => `${venue}, vuorokausikeskiarvo`,
    dailyMeanNote: (mean: string) =>
      `Vertailuksi viimeiset 30 havaittua vuorokautta: ${mean} vuorokaudessa.`,
    panelTitle: (venue: string) => `${venue}: ennuste`,
    panelDescription:
      'Katkoviiva on mediaaniennuste ja vaalea alue sen p10 - p90 -väli. Mallivalitsin vaihtaa mallia, tarkkuusvalitsin tunti- ja päivätason välillä. Legenda kertoo kummankin mallin backtest-MAE:n lähihorisontilla.',
    panelFootnote: (from: string) =>
      `Vuorokaudesta ${from} alkaen tausta on vaalean ruskea ja viiva pisteviiva: näiden vuorokausien sää on klimatologiaa, ei sääennustetta. Ero näkyy myös harmaasävyisenä.`,
    panelAria: (venue: string) =>
      `Ennustekaavio: ${venue}, mediaaniennuste ja p10 - p90 -väli 30 vuorokaudelle ja 7 vuorokaudelle tunneittain.`,
    panelAlternative: (
      venue: string,
      model: string,
      from: string,
      to: string,
      total: string,
      weatherDays: number,
      climFrom: number,
      horizon: number,
      mae: string,
    ) =>
      `${venue}: ${model} ennustaa vuorokausille ${from} - ${to} yhteensä ${total} mediaanina. Vuorokaudet 1-${weatherDays} nojaavat sääennusteeseen, vuorokaudet ${climFrom}-${horizon} klimatologiaan. Backtest-MAE lähihorisontilla on ${mae} kävijätapahtumaa vuorokaudessa.`,
    tableCaption: (venue: string, model: string) => `${venue}: ${model}, 30 vuorokauden ennuste`,
    horizonColumn: 'Vrk',
    weatherSource: 'Sään lähde',
    weatherAndHolidays: 'Sää ja pyhät',
    comparisonHeading: 'Mallien vertailu',
    comparisonLead: (model: string) =>
      `Sama luku kummallekin mallille horisonttikoreittain. Pienempi MAE on parempi. Tuotantomalli on ${model}, koska se on ainoa joka voittaa molemmat vertailukohdat molemmilla venueilla. Tarkemmat mittarit ja vertailukohdat ovat`,
    comparisonLink: 'laatusivulla',
    comparisonCaption: 'Backtest-MAE malleittain ja horisonttikoreittain',
    maeFor: (bucket: string) => `MAE ${bucket}`,
    granularityDaily: '30 vrk, päivä',
    granularityHourly: '7 vrk, tunti',
    bothModels: 'Molemmat',
    maeNote: (value: string) => `backtest-MAE 1-7 vrk ${value}`,
  },

  quality: {
    title: 'Laatu',
    heading: 'Mallien laatu: mitä backtest kertoo',
    description:
      'Backtest-mittarit, ennuste vastaan toteuma, peittävyys ja vertailu yksinkertaisiin vertailukohtiin.',
    lead: 'Kaikki tämän sivun luvut on mitattu, ei arvioitu. Ne tulevat rolling origin -backtestistä, jossa malli koulutetaan yhä uudelleen menneisiin origoihin ja ennustetaan 30 vuorokautta eteenpäin. Peittävyys mitataan jättämällä pisteytettävä origo pois välien sovituksesta, joten se ei ole määritelmällisesti 80 prosenttia.',
    scaleTitle: 'Suhteuta luvut tasoon',
    scaleBody: (venue: string, mae: string, mean: string, share: string) =>
      `Perusmallin paras MAE on venuella ${venue} ${mae} kävijätapahtumaa vuorokaudessa, kun venuen keskimääräinen vuorokausi on ${mean}. Virhe on siis noin ${share} prosenttia tasosta. Nämä ennusteet kertovat viikkorytmin ja karkean tason, eivät yksittäisen vuorokauden kävijämäärää.`,
    venueLead: (trainingDays: string, origins: string, from: string, to: string) =>
      `${trainingDays} koulutusvuorokautta, ${origins} origoa, backtest-ikkuna ${from} - ${to}. Koulutus päättyy aina origoon, myös tasopiirteiden ja tuntiprofiilin osalta.`,

    maeTitle: 'MAE horisontin mukaan',
    maeDescription:
      'Keskimääräinen itseisvirhe sen mukaan kuinka monta vuorokautta ennuste on origosta. Mukana myös kaksi yksinkertaista vertailukohtaa: sama viikonpäivä viimeksi ja 28 vuorokauden liukuva keskiarvo.',
    maeFootnote:
      'Jokainen piste on keskiarvo vain 8-10 havainnosta, joten käyrät heiluvat. Merkitsevä on taso ja mallien keskinäinen järjestys, ei yksittäinen piikki.',
    maeAria: (venue: string) =>
      `Viivakaavio: ${venue}, keskimääräinen itseisvirhe horisontin funktiona neljälle mallille.`,
    maeAxis: 'Horisontti, vuorokautta origosta →',
    metricsCaption: (venue: string) => `${venue}: mittarit malleittain ja horisonttikoreittain`,
    bias: 'Harha',
    coverage80: 'Peittävyys 80 %',

    backtestTitle: 'Ennuste vastaan toteuma',
    backtestDescription:
      'Jokainen piste on yksi ennuste ja sitä vastaava toteuma backtestissä. Lävistäjä on täydellinen osuma: pisteen etäisyys siitä on virhe. Väri ja symboli kertovat horisonttikorin.',
    backtestFootnote:
      'Ristit ovat pareja joissa toteuma jäi p10 - p90 -välin ulkopuolelle. Tavoitteena on että näitä on 20 prosenttia.',
    backtestAria: (venue: string) =>
      `Hajontakuvio: ${venue}, ennuste vaaka-akselilla ja toteuma pystyakselilla backtestissä.`,
    backtestAlternative: (pairs: string, origins: string) =>
      `Backtestissä on ${pairs} ennuste ja toteuma -paria ${origins} origosta. Peittävyys ja muut mittarit ovat yllä olevassa taulukossa. Harha on lähes kaikkialla positiivinen: mallit yliarvioivat, koska kävijämäärä laskee kevään mittaan ja origoon lukittu taso ei seuraa laskua.`,
    bandsCaption: (venue: string) => `${venue}: ennustevälien kertoimet horisonttikoreittain`,
    p10Factor: 'p10 kerroin',
    p90Factor: 'p90 kerroin',

    benchmarkTitle: 'Voittaako malli vertailukohdat',
    benchmarkLead:
      'Suhdeluku alle yhden tarkoittaa että malli on vertailukohtaa parempi. Vertailukohdat ovat tarkoituksella tyhmiä: jos malli ei voita niitä, sitä ei kannata ylläpitää.',
    benchmarkCaption: (venue: string) => `${venue}: suhde vertailukohtiin`,
    benchmarkColumn: (benchmark: string) => `MAE-suhde: ${benchmark}`,

    crossRefTitle: 'Tämä sivu mittaa tuotantoputkea',
    crossRefBody:
      'Laatusivun luvut tulevat liukuvan origon backtestistä, ja niistä johdetaan ne ennustevälit joita julkaistu ennuste kantaa. Ne päivittyvät joka ajolla. Kysymykseen ”voittiko malli yksinkertaisen säännön valitulla jaksolla” vastaa tarkkuussivu, jonka luvut päivittyvät vasta kun joku ajaa arvioinnin.',
    crossRefLink: 'Siirry tarkkuussivulle',

    limitsHeading: 'Tunnetut rajoitteet',
    limitsLead:
      'Nämä on kirjattu jokaisen venuen metrics.json-tiedoston kenttään do_not_trust. Ne eivät ole arvauksia siitä mikä voisi mennä pieleen, vaan lista tilanteista joissa mitattu tarkkuus ei päde.',
    lowCoverage: (entries: string) =>
      `Peittävyys jäi alle 70 prosentin näissä: ${entries}. Näiden ennustevälit ovat liian kapeat.`,
    lowCoverageEntry: (venue: string, model: string, bucket: string, coverage: string) =>
      `${venue}, ${model}, ${bucket} (${coverage} %)`,
    limitBenchmarks:
      'Vertailukohdat ovat lähellä. 28 vuorokauden liukuva keskiarvo, joka sivuuttaa viikonpäivän kokonaan, jää lähihorisontilla vain muutaman prosentin perusmallista. Suurin osa mallin arvosta on viikkorytmissä.',
    limitWeather:
      'Backtest käyttää horisonteilla 1-16 toteutunutta säätä, kun tuotanto käyttää sääennustetta. Sääennusteen oma virhe ei siis näy näissä luvuissa. Tämä on tiedostettu optimismi.',
    limitYearly:
      'Kumpikaan malli ei opi vuosikausivaihtelua, koska aineistossa ei ole yhtään täyttä vuotta. Vuodenaikapiirteet mittaavat tässä kevään kulkua, eivät vuosikautta.',
  },

  accuracy: {
    title: 'Tarkkuus',
    heading: 'Ennustemallin tarkkuustestit',
    description:
      'Tallennetut arviointiajot: kouluta tähän asti, ennusta tämä jakso, voittiko malli yksinkertaisen säännön.',
    lead: 'Jokainen tämän sivun ajo vastaa yhteen kysymykseen: malli koulutettiin kaikella datalla origoon asti, sen jälkeen ennustettiin valittu jakso, ja tulosta verrattiin yksinkertaiseen sääntöön. Verdikti on laskettu valmiiksi arviointiajossa ja luetaan tähän sellaisenaan, myös silloin kun se on mallia vastaan.',

    compareTitle: 'Tämä sivu ja laatusivu vastaavat eri kysymykseen',
    compareAccuracy:
      'Tämä sivu mittaa valittuja ikkunoita: kouluta tähän asti, ennusta tämä jakso, voittiko malli yksinkertaisen säännön. Se päivittyy kun joku ajaa arvioinnin.',
    compareQuality:
      'Laatusivu mittaa tuotantoputkea: liukuvan origon backtest, josta johdetaan ne ennustevälit joita julkaistu ennuste kantaa. Se päivittyy joka ajolla.',
    compareLink: 'Siirry laatusivulle',

    emptyTitle: 'Yhtään arviointiajoa ei ole tallennettu',
    emptyBody:
      'Arviointi on valinnainen työvaihe, toisin kuin datan haku ja ennusteen ajo. Kun ensimmäinen ajo on tallennettu hakemistoon data/evaluations, se ilmestyy tälle sivulle seuraavassa buildissa.',
    emptyHint: 'Yksi kuukausi kerrallaan tai monen ikkunan kooste:',

    runsHeading: 'Tallennetut arviointiajot',
    runsLead:
      'Koosteet ensin, sitten yksittäiset ikkunat, kummatkin uusin ensin. Valittu ajo tallentuu osoitteeseen, joten yksittäisen ajon voi jakaa linkkinä.',
    runsLabel: 'Valitse arviointiajo',
    sweepBadge: (windows: string) => `Kooste, ${windows} ikkunaa`,
    windowBadge: 'Yksittäinen ikkuna',
    runModels: (models: string) => `Mallit: ${models}`,
    runSelected: 'Näkyvissä',
    runFallbackNote:
      'Ilman JavaScriptiä sivu näyttää uusimman koosteen. Valitsin vaihtaa näkymää heti kun sivun skriptit ovat latautuneet.',

    verdictBetter: 'parempi kuin vertailukohta',
    verdictNoDifference: 'ei havaittavaa eroa',
    verdictWorse: 'huonompi kuin vertailukohta',
    verdictBetterShort: 'parempi',
    verdictNoDifferenceShort: 'ei eroa',
    verdictWorseShort: 'huonompi',

    verdictHeading: 'Verdikti',
    verdictAria: (venue: string) => `${venue}: verdikti ja sen luvut`,
    meanDifferenceLabel: 'Keskiero',
    meanDifferenceHelp:
      'Mallin keskimääräinen päivävirhe miinus vertailukohdan. Negatiivinen tarkoittaa että malli on lähempänä.',
    intervalLabel: (low: string, high: string) => `95 % väli ${low} … ${high}`,
    referenceLine: (reference: string) => `Päävertailukohta: ${reference}`,
    maePair: (model: string, modelMae: string, reference: string, referenceMae: string) =>
      `${model} ${modelMae}, ${reference} ${referenceMae} kävijätapahtumaa vuorokaudessa`,
    referenceMaeOnly: (mae: string) => `MAE ${mae} kävijätapahtumaa vuorokaudessa`,
    mdeNote: (mde: string, pct: string) =>
      `Tämä otos olisi erottanut vasta ${mde} kävijän eron, eli ${pct} vertailukohdan MAE:sta. ”Ei havaittavaa eroa” ei siis tarkoita samanveroisuutta.`,
    windowSplit: (favouring: string, opposing: string, neutral: string) =>
      `Malli oli parempi ${favouring} ja huonompi ${opposing} ikkunassa, ${neutral} ikkunassa eroa ei havaittu.`,
    pooledScope: (windows: string, days: string) => `${windows} ikkunaa, ${days} vuorokautta`,
    windowScope: (days: string) => `${days} vuorokautta`,
    skillScore: (value: string) => `Taitopistemäärä ${value}`,
    biasLine: (value: string, low: string, high: string) => `Harha ${value} (95 % väli ${low} … ${high})`,
    familySize: (size: string) => `Monivertailukorjaus: perheen koko ${size}.`,
    holmLine: (raw: string, holm: string) => `p-arvo ${raw}, Holm-korjattuna ${holm}`,

    summaryHeading: 'Verdikti sanoina',
    summaryWindowIntro: (from: string, to: string, days: string, origin: string, train: string, mode: string) =>
      `Ikkuna ${from}–${to} (${days} vrk), koulutus päättyy ${origin}, koulutusikkuna ${train}, sään tila ${mode}.`,
    summarySweepIntro: (sweep: string, windows: string, from: string, to: string, mode: string, reference: string) =>
      `Kooste (${sweep}): ${windows} ikkunaa, ${from}–${to}, sään tila ${mode}, päävertailukohta ${reference}.`,
    summaryVenueWindow: (venue: string, model: string, modelMae: string, reference: string, referenceMae: string) =>
      `${venue}: malli ${model} teki keskimäärin ${modelMae} kävijän päivävirheen, päävertailukohta ${reference} ${referenceMae}.`,
    summaryVenueSweep: (venue: string, model: string, reference: string, windows: string, days: string) =>
      `${venue}: malli ${model} vastaan ${reference}, ${windows} ikkunaa (${days} päivää).`,
    summaryBetter: (difference: string, low: string, high: string) =>
      `Malli voittaa vertailukohdan tilastollisesti: ero ${difference} kävijää päivässä (95 % väli ${low}…${high}).`,
    summaryNoDifference: (difference: string, low: string, high: string) =>
      `Eroa ei havaittu: ${difference} kävijää päivässä (95 % väli ${low}…${high}).`,
    summaryWorse: (difference: string, low: string, high: string) =>
      `Malli häviää vertailukohdalle tilastollisesti: ero ${difference} kävijää päivässä (95 % väli ${low}…${high}).`,
    summaryMde: (n: string, mde: string, pct: string) =>
      `Tämä otos (${n}) olisi erottanut vasta ${mde} kävijän eron, eli ${pct} vertailukohdan MAE:sta.`,
    summaryTotal: (predicted: string, actual: string, pct: string) =>
      `Jakson kokonaismäärä: ennuste ${predicted}, toteuma ${actual}, ero ${pct}.`,
    summaryWindowClosing:
      'Yhden ikkunan tulos on kuvaileva, ei todistava: varsinainen näyttö syntyy usean ikkunan koosteesta.',
    summarySweepClosing:
      'Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta, joten myös kooste lepää ohuen otoksen varassa.',

    seriesTitle: 'Ennuste vastaan toteuma',
    seriesDescription:
      'Toteuma yhtenäisenä viivana, mallin mediaaniennuste katkoviivana ja sen p10 - p90 -väli vaaleana alueena. Vertailukohdat saa näkyviin valitsimesta.',
    seriesFootnote:
      'Pystyviivat ovat pyhäpäiviä. Kuvasta luetaan mihin suuntaan ennuste karkasi ja pysyikö toteuma välin sisällä, ei sitä kumpi malli voitti: siihen vastaa ero vertailukohtaan.',
    seriesStitched:
      'Kooste piirtää jäsenikkunansa peräkkäin, kukin omasta origostaan ennustettuna. Kyseessä ei siis ole yksi yhtenäinen ennuste.',
    seriesAria: (venue: string) => `Viivakaavio: ${venue}, ennuste ja toteuma testijaksolla.`,
    seriesMissing:
      'Tämän ajon päiväsarjaa ei ole paketissa. Aikasarjat otetaan mukaan vain uusimmista ajoista, jotta sivun paino pysyy kurissa; verdikti ja mittarit ovat silti mukana.',
    seriesCaption: (venue: string) => `${venue}: ennuste ja toteuma päivittäin`,

    horizonTitle: 'Virhe horisontin mukaan',
    horizonDescription:
      'Keskimääräinen itseisvirhe horisonttikoreittain: mallit ja kaikki kolme vertailukohtaa rinnakkain.',
    horizonFootnote:
      'Tästä luetaan missä kohtaa horisonttia ennuste hajoaa. Korit ovat pieniä, tyypillisesti 7 - 16 vuorokautta, joten yksittäinen pylväs heiluu.',
    horizonAria: (venue: string) => `Ryhmitelty pylväskaavio: ${venue}, MAE horisonttikoreittain malleittain.`,
    horizonCaption: (venue: string) => `${venue}: MAE horisonttikoreittain`,

    diffTitle: 'Ero vertailukohtaan luottamusväleineen',
    diffDescription:
      'Keskiero ja sen 95 prosentin väli. Nolla on korostettu: kun koko väli on sen toisella puolella, ero on tilastollisesti havaittu.',
    diffFootnote:
      'Tämä on sivun tärkein kuva, koska verdikti luetaan siitä suoraan. Nollan yli menevä väli tarkoittaa ettei tämä otos erottanut malleja; lue silloin MDE.',
    diffAria: (venue: string) => `Piste ja väli -kuvaaja: ${venue}, keskiero vertailukohtaan 95 prosentin välillä.`,
    diffCaption: (venue: string) => `${venue}: keskiero vertailukohtaan`,
    diffZeroLabel: 'Nolla: ei eroa',
    diffPooledRow: 'Kooste',

    totalTitle: 'Jakson kokonaismäärä',
    totalDescription:
      'Ennustettu ja toteutunut kokonaismäärä koko jaksolta, ennusteen 80 prosentin väli mukana. Tämä on eri kysymys kuin päivätason tarkkuus.',
    totalFootnote:
      'Väliä ei summata päivien väleistä vaan se simuloidaan koulutusikkunan sisäisestä backtestistä. Päivien p10-summa ja p90-summa olisivat tähän aivan liian leveät.',
    totalAria: (venue: string) => `Pylväskaavio: ${venue}, ennustettu ja toteutunut kokonaismäärä.`,
    totalCaption: (venue: string) => `${venue}: jakson kokonaismäärä`,
    totalWarningTitle: 'Kokonaismäärän väliä ei pidä lukea tästä',
    totalWarningThin: 'Sisäkkäisessä backtestissä oli liian vähän origoja.',
    totalWarningDrifted:
      'Sisäkkäisten mallien virheissä on tasosiirtymä eikä pelkkää hajontaa, ja väli perii sen.',
    totalWarningBody: 'Lue silloin kokonaismäärän ero ja harha erikseen, älä väliä.',

    calibrationTitle: 'Kalibrointi',
    calibrationDescription:
      'Osuus vuorokausista joiden toteuma osui p10 - p90 -välille, ja sille Clopper-Pearsonin eksakti binomiväli. Tavoiteviiva on 0,80.',
    calibrationFootnote:
      'Kalibroitu tarkoittaa että 0,80 mahtuu välin sisään. Otos on pieni ja osuus lähellä yksikkövälin reunaa, joten väli on leveä eikä sitä saa lukea tarkaksi.',
    calibrationAria: (venue: string) => `Piste ja väli -kuvaaja: ${venue}, ennustevälien peittävyys.`,
    calibrationCaption: (venue: string) => `${venue}: peittävyys ja sen väli`,
    calibrationTarget: 'Tavoite 0,80',

    weatherTitle: 'Sään kolme tilaa',
    weatherDescription:
      'Sama ikkuna pisteytettynä kolmesti: toteutuneella säällä, sääennusteella ja klimatologialla. Verdikti lasketaan aina keskimmäisestä.',
    weatherFootnote:
      'Perfect on yläraja eikä tulos: se kertoo mihin malli pystyisi jos sää tiedettäisiin etukäteen. Perfectin ja climatologyn välinen ero on se osa tarkkuudesta joka lepää sään tuntemisen varassa.',
    weatherAria: (venue: string) => `Pylväskaavio: ${venue}, MAE sään kolmessa tilassa.`,
    weatherCaption: (venue: string) => `${venue}: MAE sään kolmessa tilassa`,
    weatherPerfect: 'perfect, yläraja',
    weatherOperational: 'operational, verdiktin perusta',
    weatherClimatology: 'climatology, alaraja',
    weatherGap: (value: string, pct: string) => `Sään arvo tässä ikkunassa: ${value} (${pct}).`,

    calibrationCalibrated: 'kalibroitu',
    calibrationTooNarrow: 'liian kapea',
    calibrationTooWide: 'liian leveä',
    biasUnbiased: 'ei systemaattista harhaa',
    biasOver: 'yliarvioi systemaattisesti',
    biasUnder: 'aliarvioi systemaattisesti',

    metricsTitle: 'Päivätason mittarit',
    metricsLead:
      'Mallit ja vertailukohdat samoilla riveillä. Nämä on laskettu ennusterivistä ajon pääsään tilassa; MAE on päämittari ja verdikti lepää sen varassa.',
    metricsCaption: (venue: string) => `${venue}: päivätason mittarit malleittain`,
    smapeUnreliable: 'sMAPE on merkitty epäluotettavaksi: testijaksolla on nollapäiviä.',
    smapeUnreliableShort: 'epäluotettava',
    zeroDays: (days: string) => `${days} nollapäivää`,

    windowsTitle: 'Koosteen ikkunat',
    windowsLead:
      'Yksi rivi per ikkuna. Kooste ei ole näiden keskiarvo: se uudelleenottaa kokonaisia ikkunoita, koska kaksi saman ikkunan päivää jakavat koulutusjoukon.',
    windowsCaption: (venue: string) => `${venue}: ikkunakohtaiset verdiktit`,

    worstTitle: 'Pahiten menneet päivät',
    worstLead:
      'Viisi suurinta päivävirhettä, suurin ensin. Positiivinen virhe tarkoittaa että malli yliarvioi kyseisen vuorokauden.',
    worstCaption: (venue: string) => `${venue}: viisi suurinta päivävirhettä`,

    colTestPeriod: 'Testijakso',
    colReference: 'Vertailukohta',
    colModelMae: 'Mallin MAE',
    colReferenceMae: 'Vertailun MAE',
    colDifference: 'Keskiero',
    colInterval: '95 % väli',
    colTotalInterval: '80 % väli',
    colVerdict: 'Verdikti',
    colMde: 'MDE',
    colWeekday: 'Viikonpäivä',
    colActual: 'Toteuma',
    colForecast: 'Ennuste',
    colError: 'Virhe',
    colNote: 'Huomio',
    colPinball: 'Pinball 0,1 / 0,5 / 0,9',
    colSmape: 'sMAPE',
    colCoverage: 'Peittävyys 80 %',

    limitsHeading: 'Mitä tästä ei voi päätellä',
    limitsLead:
      'Tämä on arvioinnin tärkein luku, ja se on lyhennetty tähän dokumentista docs/EVALUATION.md. Jokainen kohta on rajoite jonka ohittaminen tuottaa väärän johtopäätöksen oikeista luvuista.',
    limitSingleWindowStrong: 'Yhden ikkunan tulos on kuvaileva, ei todistava.',
    limitSingleWindowBody:
      'Yhden origon kolmisenkymmentä virhettä jakavat saman koulutusjoukon ja saman kuukauden sään, joten ne eivät ole kolmekymmentä riippumatonta havaintoa. Varsinainen näyttö on monen ikkunan kooste, jossa uudelleenotanta kohdistuu kokonaisiin ikkunoihin.',
    limitNoDifferenceStrong: '”Ei havaittavaa eroa” ei tarkoita samanveroisuutta.',
    limitNoDifferenceBody:
      'Se tarkoittaa että tämä otos ei erottanut malleja. Vain MDE erottaa yhtä hyvät mallit liian pienestä otoksesta, ja tällä aineistolla yhden kuukauden MDE on suuruusluokkaa kolmannes vertailukohdan MAE:sta. Pienet mutta todelliset parannukset jäävät siis näkymättömiin.',
    limitPerfectStrong: 'Perfect-sään luku on yläraja, ei saavutettu tulos.',
    limitPerfectBody:
      'Se pisteyttää mallin toteutuneella säällä, jota ei ole käytettävissä ennustehetkellä. Operational on paras arvaus eikä mittaus: se olettaa hyvän sääennusteen sen sijaan että käyttäisi sitä ennustetta joka origossa oli oikeasti saatavilla.',
    limitTotalStrong: 'Hyvä kokonaismäärä ei todista hyvää päivätarkkuutta eikä päinvastoin.',
    limitTotalBody:
      'Vastakkaisen merkkiset päivävirheet kumoavat toisensa summassa. Huhtikuussa yksinkertainen viikonpäivän keskiarvo osui venue 1:n kuukausisummaan alle prosentin tarkkuudella, vaikka sen päivätason virhe oli noin viidennes päivän keskiarvosta.',
    limitSmapeStrong: 'sMAPE ei kelpaa verdiktin perustaksi tällä aineistolla.',
    limitSmapeBody:
      'Nollapäivällä symmetrinen suhde saavuttaa 200 prosentin kattonsa riippumatta siitä kuinka lähellä ennuste oli. Mittari lasketaan, mutta se on merkitty epäluotettavaksi aina kun testijaksolla on nollapäiviä.',
    limitYearlyStrong: 'Vuosikausivaihtelusta ei voi sanoa mitään.',
    limitYearlyBody:
      'Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta. Vertailu toiseen vuoteen ei ole mahdollinen, eivätkä mallien vuosikausikomponentit ole arvioitavissa.',
    limitsSource: 'Koko luku on dokumentissa docs/EVALUATION.md.',
  },

  about: {
    title: 'Tietoja',
    heading: 'Mistä data tulee ja mitä luvut tarkoittavat',
    description: 'Lähteet, käsitteet, rajoitteet ja se mitä luvut eivät tarkoita.',
    lead: 'Tämä sivusto on staattinen. Kaikki data on laskettu valmiiksi build-aikana, eikä selain hae mitään ajon aikana. Sivusto rakennetaan uudelleen jokaisen datahaun jälkeen.',

    conceptsHeading: 'Keskeiset käsitteet',
    conceptEventTitle: 'Kävijätapahtuma, visitors_total',
    conceptEventBody1: 'Sisään- ja ulosmenojen summa. Yksi käynti tuottaa tyypillisesti kaksi tapahtumaa: yhden sisään ja yhden ulos. Luku',
    conceptEventStrong: 'ei ole',
    conceptEventBody2:
      'uniikkien kävijöiden määrä, eikä sitä voi puolittaa käyntimääräksi: ovella kääntyminen, henkilökunnan kulku ja saman henkilön useampi käynti kirjautuvat kaikki samaan lukuun. Sarake on tarkoituksella säilytetty summana, koska laskuri mittaa juuri sitä.',
    conceptZeroTitle: 'Aito nolla ja puuttuva havainto',
    conceptZeroBody1: 'Tuntirivillä on sarake',
    conceptZeroBody2:
      ', joka kertoo onko rivi haettu rajapinnasta vai täytetty nollalla. Suljettu tunti on aito nolla. Lämpökartassa nämä erotetaan toisistaan: aito nolla saa väriskaalan vaaleimman sävyn, havainnoton ruutu piirretään harmaana ja merkitään ristillä.',
    conceptSensorTitle: 'Sensorin käyttöönotto',
    conceptSensorVenue: (venue: string, from: string) => `${venue} raportoi ${from} alkaen`,
    conceptSensorBody:
      'Sitä edeltävät nollat kertovat asentamattomasta laitteesta, eivät tyhjästä tilasta. Ne on rajattu pois kaikista keskiarvoista, profiileista ja ennustemallin koulutuksesta.',
    conceptIntervalTitle: 'Ennustevälin p10 ja p90',
    conceptIntervalBody:
      'Ennustejakauman kymmenes ja yhdeksäskymmenes persentiili. Ne on laskettu mitatusta backtest-virheestä, eivät mallin sisäisistä oletuksista. Väli on leveä, ja se on rehellinen kuvaus siitä mitä neljän ja puolen kuukauden aineistolla voi sanoa. Ennustetta ei esitetä tällä sivustolla koskaan yhtenä lukuna ilman väliä.',
    conceptRainTitle: 'Sadepäivä ja sadetunti',
    conceptRainBody1: (mm: string) =>
      `Vuorokausi on sateinen kun sademäärä on vähintään ${mm} mm. Tunti on sadetunti kun sademäärä on vähintään 0,1 mm. Vuorokauden kynnys on sama kuin ennustemallin piirteellä`,
    conceptRainBody2: ', jotta sivusto ja malli puhuvat samasta säästä.',
    conceptCapacityTitle: 'Kapasiteetti',
    conceptCapacityBody1: (venues: string) => `Venuekohtainen kapasiteetti on ${venues} henkilöä.`,
    conceptCapacityBody2:
      'Sivusto vertaa siihen tunnin sisääntuloja. Se ei ole täyttöaste: viipymää ei mitata, joten yhtäaikaista kävijämäärää ei voi laskea tästä datasta.',

    sourcesHeading: 'Lähteet',
    sourcesLead: (when: string, version: string) =>
      `Viimeisin haku ${when}, ingest-versio ${version}.`,
    sourcesCaption: 'Datalähteet ja niiden tila viimeisimmässä ajossa',
    sourcesLabel: 'Datalähteet ja niiden tila',
    sourceColumn: 'Lähde',
    statusColumn: 'Tila',
    rowsColumn: 'Rivejä',
    windowColumn: 'Jakso',
    sourceVisitors: 'Kävijälaskurit',
    sourceVisitorsBody: 'tulevat Jaskaretailin IoT-rajapinnasta tunnin tarkkuudella, erikseen sisään ja ulos.',
    sourceWeather: 'Sää',
    sourceWeatherBody: (days: number) =>
      `tulee Open-Meteosta. Toteutunut sää on arkistodataa, tulevaisuus on sääennustetta enintään ${days} vuorokautta eteenpäin. Sen jälkeen käytetään klimatologiaa eli kymmenen vuoden keskiarvoa.`,
    sourceTickets: 'Lipunmyynti',
    sourceTicketsBody:
      'on käsin ylläpidetty CSV-tiedosto. Se ei päivity automaattisesti eikä kata kaikkia päiviä.',
    sourceCalendar: 'Pyhäkalenteri',
    sourceCalendarBody: 'on ylläpidetty tiedosto, joka kattaa Suomen arkipyhät.',
    sourceTraffic: 'Liikennelaskuri',
    sourceTrafficBody: 'on Oulun liikenteen Eco-Counter-rajapinta. Katso alla oleva huomautus.',

    trafficHeading: 'Liikennedata on kontekstidataa',
    trafficBody1: (site: string, id: string) =>
      `Laskuripiste ${site} (tunniste ${id}) on yksi mittauspiste Oulussa. Se mittaa jalankulkua ja pyöräilyä kadulla, ei kummankaan venuen kävijöitä.`,
    trafficBody2Strong: 'ei yhdistetä',
    trafficBody2a: 'Sitä',
    trafficBody2b:
      'venuekohtaiseksi kävijämittariksi, eikä se ole venue 2:n dataa. Aiemmassa sovelluksessa liikennedata oli kytketty venueen, mikä oli harhaanjohtavaa. Tässä se on omana sarjanaan ja merkitty kontekstidataksi. Se auttaa arvioimaan liikkuuko kaupungissa yleisesti tavallista enemmän vai vähemmän, ei sitä montako ihmistä kävi venuella.',
    trafficBody3: (from: string, to: string, pedestrians: string, cyclists: string, hours: string) =>
      `Jaksolla ${from} - ${to}: ${pedestrians} jalankulkijaa ja ${cyclists} pyöräilijää, ${hours} mitattua tuntia.`,

    forecastHeading: 'Ennusteesta',
    forecastLead1: (production: string, comparison: string) =>
      `Tuotantomalli on ${production}. Vertailukohtana ajetaan ${comparison}, jonka tulokset näkyvät`,
    forecastLink1: 'ennustesivulla',
    forecastAnd: 'ja',
    forecastLink2: 'laatusivulla',
    forecastLead2:
      'Molemmat mallit ennustavat päivätasolla; tuntitaso syntyy yhteisestä tuntiprofiilista, joten tuntiennusteiden summa on täsmälleen päiväennuste.',
    forecastCaption: 'Ennusteen perustiedot venueittain',
    forecastLabel: 'Ennusteen perustiedot',
    originColumn: 'Origo',
    horizonColumn: 'Horisontti',
    weatherNearColumn: 'Sään lähde, lähivuorokaudet',
    weatherFarColumn: 'Sään lähde, loppuhorisontti',
    openingColumn: 'Aukiolo',
    daysRange: (from: number, to: number) => `vrk ${from}-${to}:`,
    daysUnit: (days: number) => `${days} vrk`,
    openingHours: (hours: string) => `klo ${hours}`,

    notHeading: 'Mitä luvut eivät tarkoita',
    not1Strong: 'Kävijätapahtuma ei ole kävijä.',
    not1Body:
      'Se on laskurin havainto ovella. Kahdella tapahtumalla jakaminen antaa karkean arvion käynneistä, mutta se on arvio eikä mittaus.',
    not2Strong: 'Sään ja kävijämäärän yhteys ei ole syysuhde.',
    not2Body:
      'Aineisto kattaa tammikuusta toukokuuhun. Sinä aikana muuttuu sään lisäksi kaikki muukin: ohjelmisto, koulujen lomat, valoisuus ja matkailukausi. Näitä ei voi erottaa toisistaan tällä aineistolla.',
    not3Strong: 'Ennuste ei tunne tulevia tapahtumia.',
    not3Body:
      'Malli näkee menneet piikit datassa mutta ei tiedä ensi viikon konsertista. Tämä on suurin yksittäinen virhelähde.',
    not4Strong: 'Ennuste ei ole tarkka yksittäiselle vuorokaudelle.',
    not4Body: 'Se kertoo viikkorytmin ja karkean tason. Mitatut virheet ja niiden suuruus suhteessa tasoon ovat',
    not4Link: 'laatusivulla',
    not5Strong: 'Kapasiteettivertailu ei ole täyttöaste.',
    not5Body: 'Viipymää ei mitata.',
    not6Strong: 'Liput eivät ole kävijöitä.',
    not6Body: 'Ryhmälippu kattaa useita henkilöitä, ja osa kävijöistä tulee ilman lippua.',

    technicalHeading: 'Tekniset tiedot',
    technical1:
      'Sivusto on staattinen Astro-sivusto. Data paketoidaan JSONiksi build-aikana, eikä selain hae mitään ajon aikana. Ei palvelinreittejä, ei rajapintoja, ei ulkoisia skriptejä.',
    technical2:
      'Build kaatuu jos ingest-manifesti on yli 48 tuntia vanha, jos ennustetiedostot puuttuvat tai jos syötetiedostojen sarakkeet eivät vastaa odotettua. Vanhaa dataa ei julkaista oikeana.',
    technical3:
      'Kaikki ajat ovat Suomen aikaa myös englanninkielisessä versiossa. Kesäajan vaihtuminen on käsitelty jo aineiston puolella: paikallinen vuorokausi voi olla 23 tai 25 tuntia, ja tuntiosuudet normalisoidaan sille tuntijoukolle joka päivällä oikeasti on.',
    technical4: (built: string, age: string) =>
      `Sivusto rakennettiin ${built}, ingest-manifesti oli silloin ${age} tuntia vanha.`,
  },
};

export type Translation = typeof fi;
