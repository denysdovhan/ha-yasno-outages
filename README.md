[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua)
[![Made in Ukraine](https://img.shields.io/badge/made_in-Ukraine-ffd700.svg?labelColor=0057b7)](https://stand-with-ukraine.pp.ua)
[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/StandWithUkraine.svg)](https://stand-with-ukraine.pp.ua)
[![Russian Warship Go Fuck Yourself](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/RussianWarship.svg)](https://stand-with-ukraine.pp.ua)

[![GitHub Release][gh-release-image]][gh-release-url]
[![hacs][hacs-image]][hacs-url]

![](/icons/logo.png)

# 💡 Svitlo Yeah | Світло Є

A [Home Assistant][home-assistant] integration that tracks electricity outage schedules from Ukrainian energy providers, providing outage calendars, countdown timers, and status updates.


## Installation

The quickest way to install this integration is via [HACS][hacs-url] by clicking the button below:

[![Add to HACS via My Home Assistant][hacs-install-image]][hasc-install-url]

If it doesn't work, adding this repository to HACS manually by adding this URL:

1. Visit **HACS** → **Integrations** → **...** (in the top right) → **Custom repositories**
2. Click **Add**
3. Paste `https://github.com/ALERTua/ha-svitlo-yeah` into the **URL** field
4. Chose **Integration** as a **Category**
5. **Svitlo Yeah | Світло Є** will appear in the list of available integrations. Install it normally.

## Usage

This integration is configurable via UI. On **Devices and Services** page, click **Add Integration** and search for **Svitlo Yeah**.

Select your region:

![Region Selection](/media/1_region.png)

Select your Service Provider (if applicable)

![Service Provider Selection](/media/2_provider.png)

Select your Group

![Group Selection](/media/3_group.png)

Here's how the devices look

![Devices page](/media/4_devices.png)

![Sensors](/media/5_sensors.png)

Then you can add the integration to your dashboard and see the information about the next planned outages.
Integration also provides a calendar view of planned outages. You can add it to your dashboard as well via [Calendar card][calendar-card].

![Calendars view](/media/6_calendars.png)

Examples:

- [Automation](/examples/automation.yaml)
- [Dashboard](/examples/dashboard.yaml)


<!-- Badges -->

[gh-release-url]: https://github.com/ALERTua/ha-svitlo-yeah/releases/latest
[gh-release-image]: https://img.shields.io/github/v/release/ALERTua/ha-svitlo-yeah?style=flat-square
[gh-downloads-url]: https://github.com/ALERTua/ha-svitlo-yeah/releases
[hacs-url]: https://github.com/hacs/integration
[hacs-image]: https://img.shields.io/badge/hacs-default-orange.svg?style=flat-square

<!-- References -->

[home-assistant]: https://www.home-assistant.io/
[hasc-install-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=ALERTua&repository=ha-svitlo-yeah&category=integration
[hacs-install-image]: https://my.home-assistant.io/badges/hacs_repository.svg
[calendar-card]: https://www.home-assistant.io/dashboards/calendar/
