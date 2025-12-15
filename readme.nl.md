[![SWUbanner](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua/)

![HA Yasno Outages Logo](./icons/logo.png)

# ⚡️ HA Yasno Stroomonderbrekingen

[![GitHub Release][gh-release-image]][gh-release-url]
[![GitHub Downloads][gh-downloads-image]][gh-downloads-url]
[![hacs][hacs-image]][hacs-url]
[![GitHub Sponsors][gh-sponsors-image]][gh-sponsors-url]
[![Buy Me A Coffee][buymeacoffee-image]][buymeacoffee-url]
[![Twitter][twitter-image]][twitter-url]

> [!NOTE]
> Een integratie voor stroomonderbrekingsschema’s van [Yasno][yasno].
>
> Deze integratie is op geen enkele manier verbonden met [Yasno][yasno].  
> Ze is ontwikkeld door een individuele ontwikkelaar. Informatie kan afwijken van de officiële website.

Deze integratie voor [Home Assistant][home-assistant] geeft informatie over de stroomonderbrekingsschema’s van [Yasno][yasno]: een kalender met geplande onderbrekingen, tijdsensoren voor de volgende geplande onderbrekingen en meer.

> [!TIP]
> Документація доступна [**українською мовою 🇺🇦**](./readme.uk.md)

## Sponsoring

Jouw steun helpt mij om dit project te onderhouden en nieuwe projecten te ontwikkelen.

- 💖 [Sponsor op GitHub][gh-sponsors-url]
- ☕️ [Buy Me A Coffee][buymeacoffee-url]
- Bitcoin: `bc1q7lfx6de8jrqt8mcds974l6nrsguhd6u30c6sg8`
- Ethereum: `0x6aF39C917359897ae6969Ad682C14110afe1a0a1`

## Installatie

De snelste manier om deze integratie te installeren is via [HACS][hacs-url] door op de onderstaande knop te klikken:

[![Toevoegen aan HACS via My Home Assistant][hacs-install-image]][hasc-install-url]

Als dit niet werkt, kun je de repository handmatig toevoegen aan HACS:

1. Ga naar **HACS** → **Integrations** → **...** (rechtsboven) → **Custom repositories**
2. Klik op **Add**
3. Plak `https://github.com/denysdovhan/ha-yasno-outages` in het veld **URL**
4. Kies **Integration** als **Category**
5. **Yasno Outages** verschijnt nu in de lijst met beschikbare integraties. Installeer hem zoals gebruikelijk.

## Gebruik

Deze integratie is volledig via de UI te configureren.  
Ga naar **Devices and Services**, klik op **Add Integration** en zoek naar **Yasno Outages**.

Selecteer je regio:

![Region Selection](/media/1_region.png)

Selecteer je serviceprovider:

![Service Provider Selection](/media/2_provider.png)

Selecteer je groep:

![Group Selection](/media/3_group.png)

Zo zien de apparaten eruit:

![Devices page](/media/4_devices.png)

![Device page](/media/5_device.png)

Daarna kun je de integratie toevoegen aan je dashboard en informatie zien over de volgende geplande onderbrekingen.  
De integratie biedt ook een kalenderweergave van geplande onderbrekingen. Je kunt deze eveneens toevoegen via de [Calendar card][calendar-card].

![Calendars view](/media/6_calendars.png)

Voorbeelden:

- [Automatisering](/examples/automation.yaml)
- [Dashboard](/examples/dashboard.yaml)

Hier is een voorbeeld van een dashboard dat deze integratie gebruikt:

![Dashboard example](https://github.com/denysdovhan/ha-yasno-outages/assets/3459374/26c75595-8984-4a9f-893a-e4b6d838b7f2)

## Ontwikkeling

Wil je bijdragen aan het project?

Allereerst: bedankt! Bekijk de [contributierichtlijnen](/contributing.md) voor meer informatie.

## Licentie

MIT © [Denys Dovhan][denysdovhan]

<!-- Badges -->

[gh-release-url]: https://github.com/denysdovhan/ha-yasno-outages/releases/latest
[gh-release-image]: https://img.shields.io/github/v/release/denysdovhan/ha-yasno-outages?style=flat-square
[gh-downloads-url]: https://github.com/denysdovhan/ha-yasno-outages/releases
[gh-downloads-image]: https://img.shields.io/github/downloads/denysdovhan/ha-yasno-outages/total?style=flat-square
[hacs-url]: https://github.com/hacs/integration
[hacs-image]: https://img.shields.io/badge/hacs-default-orange.svg?style=flat-square
[gh-sponsors-url]: https://github.com/sponsors/denysdovhan
[gh-sponsors-image]: https://img.shields.io/github/sponsors/denysdovhan?style=flat-square
[buymeacoffee-url]: https://buymeacoffee.com/denysdovhan
[buymeacoffee-image]: https://img.shields.io/badge/support-buymeacoffee-222222.svg?style=flat-square
[twitter-url]: https://twitter.com/denysdovhan
[twitter-image]: https://img.shields.io/badge/twitter-%40denysdovhan-00ACEE.svg?style=flat-square

<!-- References -->

[yasno]: https://yasno.com.ua/
[home-assistant]: https://www.home-assistant.io/
[denysdovhan]: https://github.com/denysdovhan
[hasc-install-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=denysdovhan&repository=ha-yasno-outages&category=integration
[hacs-install-image]: https://my.home-assistant.io/badges/hacs_repository.svg
[add-translation]: https://github.com/denysdovhan/ha-yasno-outages/blob/master/contributing.md#how-to-add-translation
[calendar-card]: https://www.home-assistant.io/dashboards/calendar/
