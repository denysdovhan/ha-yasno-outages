[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua)
[![Made in Ukraine](https://img.shields.io/badge/made_in-Ukraine-ffd700.svg?labelColor=0057b7)](https://stand-with-ukraine.pp.ua)
[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/StandWithUkraine.svg)](https://stand-with-ukraine.pp.ua)
[![Russian Warship Go Fuck Yourself](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/RussianWarship.svg)](https://stand-with-ukraine.pp.ua)

[![GitHub Release][gh-release-image]][gh-release-url]
[![hacs][hacs-image]][hacs-url]

![logo](/icons/logo.png)

# 💡 Svitlo Yeah | Світло Є

A [Home Assistant][home-assistant] integration that tracks electricity outage schedules from Ukrainian energy providers,
providing outage calendars, countdown timers, and status updates.

###### [Цей документ українською](https://github-com.translate.goog/ALERTua/ha-svitlo-yeah/blob/main/README.md?_x_tr_sl=en&_x_tr_tl=uk&_x_tr_hl=en&_x_tr_pto=wapp)

## Supported Regions

| Region                         | Provider | Data Source                                                                                                                                                                                                                             |
|--------------------------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Kyiv**                       | DTEK     | [Yasno API](https://yasno.ua)                                                                                                                                                                                                           |
| **Dnipro**                     | DnEM     | [Yasno API](https://yasno.ua)                                                                                                                                                                                                           |
| **Dnipro**                     | CEK      | [Yasno API](https://yasno.ua)                                                                                                                                                                                                           |
| **Kyiv Oblast**                | DTEK     | [Baskerville42/outage-data-ua](https://github.com/Baskerville42/outage-data-ua/blob/main/data/kyiv-region.json)                                                                                                                         |
| **Dnipro and Oblast**          | DTEK     | [Baskerville42/outage-data-ua](https://github.com/Baskerville42/outage-data-ua/blob/main/data/dnipro.json)                                                                                                                              |
| **Odesa and Oblast**           | DTEK     | [Baskerville42/outage-data-ua](https://github.com/Baskerville42/outage-data-ua/blob/main/data/odesa.json)                                                                                                                               |
| **Khmelnytskyi and Oblast**    | KhOE     | [yaroslav2901/OE_OUTAGE_DATA](https://github.com/yaroslav2901/OE_OUTAGE_DATA/blob/main/data/Khmelnytskoblenerho.json)                                                                                                                   |
| **Ivano-Frankivsk and Oblast** | POE      | [yaroslav2901/OE_OUTAGE_DATA](https://github.com/yaroslav2901/OE_OUTAGE_DATA/blob/main/data/Prykarpattiaoblenerho.json)                                                                                                                 |
| **Uzhhorod and Oblast**        | ZOE      | [yaroslav2901/OE_OUTAGE_DATA](https://github.com/yaroslav2901/OE_OUTAGE_DATA/blob/main/data/Zakarpattiaoblenerho.json)                                                                                                                  |
| **Lviv and Oblast**            | LOE      | [yaroslav2901/OE_OUTAGE_DATA](https://github.com/yaroslav2901/OE_OUTAGE_DATA/blob/main/data/Lvivoblenerho.json)                                                                                                                         |
| **Ternopil and Oblast**        | TOE      | [yaroslav2901/OE_OUTAGE_DATA](https://github.com/yaroslav2901/OE_OUTAGE_DATA/blob/main/data/Ternopiloblenerho.json)                                                                                                                     |
| **Chernihiv and Oblast**       | ChOE     | [yaroslav2901/OE_OUTAGE_DATA](https://github.com/yaroslav2901/OE_OUTAGE_DATA/blob/main/data/Chernihivoblenergo.json)                                                                                                                    |
| **Zaporizhzhia and Oblast**    | ZOE      | [yaroslav2901/OE_OUTAGE_DATA](https://github.com/yaroslav2901/OE_OUTAGE_DATA/blob/main/data/Zaporizhzhiaoblenergo.json)                                                                                                                 |
| **Zhytomyr and Oblast**        | ZhOE     | [yaroslav2901/OE_OUTAGE_DATA](https://github.com/yaroslav2901/OE_OUTAGE_DATA/blob/main/data/Zhytomyroblenergo.json)                                                                                                                     |
| **Poltava and Oblast**         | POE      | [yaroslav2901/OE_OUTAGE_DATA](https://github.com/yaroslav2901/OE_OUTAGE_DATA/blob/main/data/Poltavaoblenergo.json)                                                                                                                      |
| **Rivne and Oblast**           | ROE      | [yaroslav2901/OE_OUTAGE_DATA](https://github.com/yaroslav2901/OE_OUTAGE_DATA/blob/main/data/Rivneoblenergo.json)                                                                                                                        |
| **Vinnytsia and Oblast**       | VOE      | [olnet93/gpv-voe-vinnytsia](https://github.com/olnet93/gpv-voe-vinnytsia/blob/main/data/Vinnytsiaoblenerho.json)<br/>[vn-progr/gpv-voe-vinnytsia](https://github.com/vn-progr/gpv-voe-vinnytsia/blob/main/data/Vinnytsiaoblenerho.json) |
| **Sumy and Oblast**            | SOE      | [Alerts Energy JSON API](https://alerts.energy/api/v1/source-registry/areas/sumska-oblast/shutdowns)                                                                                                                                                                                             |

## Installation

The quickest way to install this integration is via [HACS][hacs-url] by clicking the button below:

[![Add to HACS via My Home Assistant][hacs-install-image]][hasc-install-url]

If it doesn't work, adding this repository to HACS manually by adding this URL:

1. Visit **HACS** → **Integrations** → **...** (in the top right) → **Custom repositories**
2. Click **Add**
3. Paste `https://github.com/ALERTua/ha-svitlo-yeah` into the **URL** field
4. Choose **Integration** as a **Category**
5. **Svitlo Yeah | Світло Є** will appear in the list of available integrations. Install it normally.

## Usage

This integration is configurable via UI. On **Devices and Services** page, click **Add Integration** and search for **Svitlo Yeah**.

### Setup parameters

Before you start, find your outage group on the website of your provider. For Sumy and Oblast, select your Sumyoblenergo subgroup, for example `4.1`, from [Alerts Energy](https://alerts.energy/sumska-oblast). No login or personal account is needed.

| Step | Field | Description |
|---|---|---|
| Select Region/System Distribution | Select your region/system distribution | The region or the distribution system operator that supplies electricity to your address. The list has each region of [Supported Regions](#supported-regions). |
| Outdated schedule data | I understand and accept the risk | Shows only when no DTEK JSON source of the region has fresh data. Select it to pick your group from the outdated schedule. See [Outdated schedule data](#outdated-schedule-data-dtek-json). |
| Settings | Select your group | Your outage group, for example `1.1`. Find it on the website of your provider, for example [Yasno](https://static.yasno.ua/kyiv/outages) or [DTEK](https://www.dtek-krem.com.ua/ua/shutdowns). For DTEK Dnipro, the list shows a CEK group with its number in the source, for example «ЦЕК 1.1 (1001.1)». |
| Sumyoblenergo schedule | Select your subgroup | Your Sumyoblenergo subgroup, for example `4.1`. Only Sumyoblenergo groups are supported. |

Each region and group is a separate entry. To change the group of a DTEK, Yasno or Sumy entry later, open the menu of the entry and select **Reconfigure**. It shows the **Select your group** field again.

The integration gives a new entry the name of its device in the language of your Home Assistant, for example «Київ ДТЕК 52.1». The name of a Sumy entry and its device contains the subgroup, for example «Суми Alerts Energy 4.1». Existing Sumy entries migrate locally from E-Svitlo and keep their devices, all nine entities and entity IDs, and user-given names. If the old cache has no reliable subgroup, open the entry menu and select **Reconfigure**; until then, Electricity shows Unknown. The same happens to the English name of a DTEK Kyiv Oblast device: «Kyiv Region 1.1» becomes «Kyiv Oblast 1.1». To update the entity IDs, open the device and select **Recreate entity IDs**. Reconfigure puts the new group into a name that the integration gave, and keeps a name that you gave. An entry from an earlier version keeps the name «Svitlo Yeah | Світло Є» until you rename it or Reconfigure changes its group.

<details>
<summary>Screenshots of the setup</summary>

![Region Selection](/media/1_region.png)

![Group Selection](/media/3_group.png)

</details>

### Outdated schedule data (DTEK JSON)

When there are no outages for a while, DTEK JSON sources may stop publishing and all data becomes outdated. In that case setup shows a confirmation step: you can still pick your group from the last-known schedule after acknowledging the risk. The step shows when the source last updated the schedule, in Kyiv time. Once outages resume, double-check that your group hasn't changed.

The outdated data serves only the choice of the group, and the integration does not use it after setup. The integration keeps the last fresh schedule of each entry, also across a restart of Home Assistant. If a source becomes outdated or does not answer, the integration uses that schedule until the source publishes fresh data again, also when that schedule gets older. The **Schedule Updated On** sensor shows the update time of the schedule that the integration uses.

### Sumy schedules

Alerts Energy supplies the dated hourly schedules for Sumyoblenergo. Only confirmed planned intervals are shown; possible-outage calendars stay empty. An unpublished or emergency-marked day is Unknown. If possible hours are present, Electricity shows Unknown outside confirmed intervals. A published schedule with no outages means Connected. The integration never copies today’s schedule to tomorrow. A failed request keeps the last schedule, including its original dates; a valid unpublished schedule replaces the old schedule for that day.

Before updating a working Home Assistant, back up its configuration and the `svitlo_yeah.<entry_id>` stored schedule, and check the migration on a test instance. To roll back, restore both the previous integration version and the backup.

### Here's how the devices look

<details>
<summary>The device page</summary>

![Devices page](/media/4_devices.png)

</details>

<details>
<summary>The sensors</summary>

![Sensors](/media/5_sensors.png) ![Sensors 2](/media/5_1_sensors.png)

</details>

### Calendar View

Then you can add the integration to your dashboard and see the information about the next planned outages.
Integration also provides a calendar view of planned outages. You can add it to your dashboard as well
via [Calendar card][calendar-card].

<details>
<summary>The calendars</summary>

![Calendars view](/media/6_calendar.png)

</details>

### Examples

- [Automation](/examples/automation.yaml)
- [Dashboard](/examples/dashboard.yaml)

<details>
<summary>The dashboard of the example</summary>

![dashboard](media/7_dashboard.png)

</details>

## Integration Entities

The integration creates the following entities in Home Assistant:

### Sensors

| Entity                                                                                   | Type             | Purpose                                                          | Description                                                                                                                                                                                                                                                                                                                                              |
|------------------------------------------------------------------------------------------|------------------|------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Electricity**                                                                          | Enum Sensor      | Shows current power connectivity state according to the calendar | Indicates the current electricity status with three possible states: `connected` (normal power), `planned_outage` (scheduled blackout), or `emergency` (unscheduled blackout). Shows `unknown` while the source has no schedule for the configured group. Shows `connected` while the integration has no DTEK schedule, for example for a new entry while the source has no fresh data, because the integration has no outage events then. Reflects the calendar state and shows if there is an ongoing outage event at the moment. Provides additional attributes including event details when an outage is active. |
| [**Schedule Updated On**](/custom_components/svitlo_yeah/translations/uk.json#L97)       | Timestamp Sensor | Shows when outage schedule was last updated by the provider      | Displays the timestamp when the energy provider last updated the outage schedule on their servers. Reflects server-side data changes, not client fetch times.                                                                                                                                                                                            |
| [**Schedule Data Changed On**](/custom_components/svitlo_yeah/translations/uk.json#L100) | Timestamp Sensor | Shows when actual outage schedule data changed                   | Tracks the timestamp when the actual data was modified. Useful for notifications when schedules are updated. See examples.                                                                                                                                                                                                                               |
| [**Next Planned Outage**](/custom_components/svitlo_yeah/translations/uk.json#L104)      | Timestamp Sensor | Shows the start time of the next planned outage                  | Displays the timestamp when the upcoming planned outage is planned to begin. Null when there are no planned outages.                                                                                                                                                                                                                                     |
| [**Next Scheduled Outage**](/custom_components/svitlo_yeah/translations/uk.json#L107)    | Timestamp Sensor | Shows the start time of the next scheduled outage                | Displays the timestamp of the upcoming scheduled outage event, comparing scheduled outages and planned outages to show whichever comes first. Null when no outages are scheduled or planned.                                                                                                                                                             |
| [**Next Connectivity**](/custom_components/svitlo_yeah/translations/uk.json#L109)        | Timestamp Sensor | Shows when power is expected to return                           | Displays the timestamp when power connectivity is expected to be restored after an outage. Null when no outages are active.                                                                                                                                                                                                                              |

**Scheduled vs Planned Outages:**
- **Scheduled Outage**: Time windows when outages MAY happen (potential outage periods that are scheduled for your Outage Group)
- **Planned Outage**: Confirmed outages that WILL happen (actual outage periods for your Outage Group)

### Calendar

| Entity                         | Type            | Purpose                                           | Description                                                                                                                                                                                                                                                    |
|--------------------------------|-----------------|---------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Planned Outages Calendar**   | Calendar Entity | Provides calendar integration for planned outages | Shows all planned power outages as calendar events. Can be used with Home Assistant's calendar cards, automations, and triggers. Events include "Definite" planned outages and "Emergency" unscheduled blackouts. The calendar state is `on` during any event. |
| **Scheduled Outages Calendar** | Calendar Entity | Provides calendar integration for outage schedule | Shows the power outages schedule.                                                                                                                                                                                                                              |

### Button

| Entity                | Type          | Purpose                                            | Description                                                                                                                                                                                 |
|-----------------------|---------------|----------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Force refresh now** | Button Entity | Forces an immediate refresh of the outage schedule | Triggers a data refresh right away, ignoring the regular update interval. Useful to pull a freshly published schedule without waiting. Data still refreshes automatically on its own timer. If the source does not answer, the press fails with an error, and the entities keep the last schedule. An outdated DTEK schedule is not an error. If an automation presses the button, add `continue_on_error: true` to that step, so that the automation does not stop on the error. |

### Events

| Event                        | Description                             |
|------------------------------|-----------------------------------------|
| **svitlo_yeah_data_changed** | Fired when outage data actually changes |

<details>
<summary>Examples of the event data, for Yasno and for a DTEK JSON source</summary>

```yaml
event_type: svitlo_yeah_data_changed
data:
  region_name: Київ  # yes, Cyrillic. This is how it comes from the API
  region_id: 25
  provider_id: 902
  provider_name: ПРАТ «ДТЕК КИЇВСЬКІ ЕЛЕКТРОМЕРЕЖІ»
  group: "3.1"
  last_data_change: "2025-11-15T14:20:24.627353+02:00"
  config_entry_id: 01KB817HS8R32RSYH5RW01G78Z
```

```yaml
event_type: svitlo_yeah_data_changed
data:
  region_name: odesa
  region_id: null
  provider_id: null
  provider_name: null
  group: "1.1"
  last_data_change: "2025-11-15T14:20:24.627353+02:00"
  config_entry_id: 01KB817S4AXVFB39X97NGYCV55
```

</details>

### Entity Usage Examples

- Use the **Electricity** sensor in dashboards to display current power status from the calendar perspective
- Set up notifications when **Schedule Data Changed On** updates to alert about schedule changes
- Or use the event to trigger on (described above and in [automation examples](/examples/automation.yaml))
- Use the **Planned Outages Calendar** with calendar triggers for advance warnings before outages
- Monitor **Next Planned Outage** and **Next Connectivity** timestamps for countdown displays

### Caveats

<details>
<summary>How to get your Yasno group</summary>

[![video example](/media/yasno_group.gif)](/media/yasno_group.gif)

</details>

- This project is intended to be used as a Home Assistant / HACS integration, not as a standalone Python library — the API classes require a Home Assistant instance. If you'd like the code to be usable outside the HACS integration as a plain Python library, let me know and I'll consider adding support for that.

## Data updates

The integration asks the source of each entry for the outage schedule every 15 minutes. The source is the Yasno API, the Alerts Energy JSON API, or a JSON file on GitHub that a community project updates for a DTEK region (see [Supported Regions](#supported-regions)). Between two updates, each entity changes its state exactly at the start and at the end of an outage, without a new request. To update now, press the **Force refresh now** button of the entry, or call the `homeassistant.update_entity` action on one of its entities.

The integration keeps the last schedule of each entry, also across a restart of Home Assistant. If the source does not answer, or a DTEK source has no data newer than 2 days, the entities keep the last schedule until the source gives fresh data. The integration then writes one line to the log, and one more line when the source answers again.

## Known limitations

- The **Next Planned Outage**, **Next Scheduled Outage** and **Next Connectivity** sensors look 24 hours ahead. An outage that starts later shows only in the calendars.
- A DTEK JSON source is a community copy of the DTEK schedule. It can come later than the website of DTEK, and it has no emergency outages.
- Alerts Energy serves Sumyoblenergo subgroups in Sumy and Sumy Oblast only. Emergency status endpoints and possible outage intervals are not used.
- The update interval is 15 minutes, and you cannot change it.
- Reconfigure changes the group of an entry, but not its entity IDs. To update them, open the device and select **Recreate entity IDs**.
- One entry shows one group. For another group, add one more entry. Existing Sumy entries for different old personal accounts are kept separately, even if they have the same subgroup.

## Troubleshooting

<details>
<summary>Electricity shows Unknown, and Repairs shows «No outage schedule for group …»</summary>

**Description:** the source has no schedule for the group of the entry. The provider can renumber or remove groups.

**Resolution:**

1. Find your current group on the website of your provider.
2. Go to **Settings** → **Devices & services** → **Svitlo Yeah!**, open the menu of the entry, and select **Reconfigure**.
3. Select the group. The repair message disappears when the source has the group.

</details>

<details>
<summary>The schedule does not change, and Schedule Updated On is old</summary>

**Description:** the source does not answer, or a DTEK source has no fresh data. The entities show the last schedule that the integration got. The log has the line «The source of provider … does not answer» when the source does not answer.

**Resolution:**

1. Press **Force refresh now**. If the source does not answer, the press shows an error.
2. Compare the schedule with the website of your provider. A DTEK JSON source can come later than the website.
3. Wait for the next update. The entities change when the source gives fresh data.

</details>

<details>
<summary>The setup stops with «No data source gave a schedule…» or «Failed to get the Yasno groups»</summary>

**Description:** the source did not answer during the setup, or it has no groups now.

**Resolution:** make sure that Home Assistant can connect to the Internet, and add the integration again later.

</details>

<details>
<summary>Sumy asks to select a subgroup after an update</summary>

**Resolution:** open the menu of the existing entry, select **Reconfigure**, and select your Sumyoblenergo subgroup. Do not delete the entry: its devices and entities are kept.

</details>

<details>
<summary>The entry shows «Failed to set up»</summary>

**Description:** the entry has no setting that the integration needs, or it has a DTEK source that this version of the integration does not have. The message names the reason.

**Resolution:** delete the entry, and add it again.

</details>

To report a problem, get the debug log and the diagnostics, as the [troubleshooting guide of Home Assistant](https://www.home-assistant.io/docs/configuration/troubleshooting/) tells:

1. Go to **Settings** → **Devices & services** → **Svitlo Yeah!**. Open the three dots **⋮** menu at the top right, and select **Enable debug logging**.
2. Make the problem happen again, for example press **Force refresh now**.
3. In the same menu, select **Disable debug logging**, and save the log file.
4. Open the menu of the entry, and select **Download diagnostics**. The diagnostics redact any legacy login, password, personal account or address.
5. Open an issue on [GitHub](https://github.com/ALERTua/ha-svitlo-yeah/issues), and attach both files.

## Removing the integration

This integration follows standard integration removal. Each entry keeps its last schedule in the storage of Home Assistant. When you delete an entry, Home Assistant removes its device and its entities, and the integration removes its repair issue and its stored schedule.

Each provider and group is a separate entry. To remove an entry:

1. Go to **Settings** → **Devices & services**, and select the **Svitlo Yeah!** card.
2. Next to the entry that you want to remove, select the three dots **⋮** menu.
3. Select **Delete**.

To remove the integration files too, delete all entries first. Then open **HACS**, find **Svitlo Yeah | Світло Є**, select the three dots **⋮** menu, and select **Remove**. Restart Home Assistant.

Automations, scripts and dashboards that use the entities or the `svitlo_yeah_data_changed` event stay. Change or delete them yourself.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for information about adding new regions and contributing to the project.

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
