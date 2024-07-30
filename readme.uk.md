[![SWUbanner](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua/)

![HA Yasno Outages Logo](./icons/logo.png)

# ⚡️ HA Yasno Outages

[![GitHub Release][gh-release-image]][gh-release-url]
[![GitHub Downloads][gh-downloads-image]][gh-downloads-url]
[![hacs][hacs-image]][hacs-url]
[![GitHub Sponsors][gh-sponsors-image]][gh-sponsors-url]
[![Patreon][patreon-image]][patreon-url]
[![Buy Me A Coffee][buymeacoffee-image]][buymeacoffee-url]
[![Twitter][twitter-image]][twitter-url]

> Інтеграція для графіків відключень електроенергії від [Yasno][yasno].

Ця інтеграція надає інформацію про графіки відключень електроенергії від [Yasno][yasno]: календар запланованих відключень, датчики часу для наступних запланованих відключень, тощо.

**💡 Примітка:** Цей проєкт не має жодного відношення до [Yasno][yasno]. Ця інтеграція розроблена ентузіастом. Інформація може відрізнятися від інфомації на офіційному сайті.

## Спонсорство

Ваша щедрість допоможе мені підтримувати та розробляти більше таких проектів, як цей.

- 💖 [Спонсорувати на GitHub][gh-sponsors-url]
- ☕️ [Buy Me A Coffee][buymeacoffee-url]
- 🤝 [Підтримати на Patreon][patreon-url]
- Bitcoin: `bc1q7lfx6de8jrqt8mcds974l6nrsguhd6u30c6sg8`
- Ethereum: `0x6aF39C917359897ae6969Ad682C14110afe1a0a1`

## Встановлення

Найшвидший спосіб встановити цю інтеграцію через [HACS][hacs-url], натиснувши кнопку нижче:

[![Add to HACS via My Home Assistant][hacs-install-image]][hasc-install-url]

Якщо це не працює, додайте цей репозиторій в HACS вручну, додавши цей URL:

1. Відвідайте **HACS** → **Інтеграції** → **...** (вгорі праворуч) → **Користувацькі репозиторії**
1. Натисніть **Додати**
1. Вставте `https://github.com/denysdovhan/ha-yasno-outages` у поле **URL**
1. Виберіть **Інтеграція** як **Категорію**
1. **Yasno Outages** з'явиться у списку доступних інтеграцій. Встановіть її звичайним способом.

## Використання

Ця інтеграція налаштовується через інтерфейс користувача. На сторінці **Пристрої та сервіси** натисніть **Додати інтеграцію** і знайдіть **Yasno Відключення**.

Виберіть своє місто:

![image](https://github.com/user-attachments/assets/0d3492d8-54ee-49cc-a09d-40934fcdfc6d)

Знайдіть свою групу, відвідавши вебсайт [Yasno][yasno] і введіть свою адресу в пошуковий рядок. Виберіть свою групу в конфігурації.

![Configuration flow](https://github.com/denysdovhan/ha-yasno-outages/assets/3459374/e8bfde50-fcbe-45c3-b448-b451b0ac3bcd)

Потім ви можете додати інтеграцію на свою панель і бачити інформацію про наступні заплановані відключення.

![Device page](https://github.com/denysdovhan/ha-yasno-outages/assets/3459374/df628647-fd2a-455d-9d08-0d1542b67e41)

Інтеграція також надає календар запланованих відключень. Ви можете використати [Картку календаря][calendar-card], щоб додати його на свою інформаційну панель.

![Calendar view](https://github.com/denysdovhan/ha-yasno-outages/assets/3459374/b09c4db3-d0a0-4e06-8dd9-3f4a59f1d63e)

Ось приклад інформаційної панелі використовуючи цю інтеграцію:

![Dashboard example](https://github.com/denysdovhan/ha-yasno-outages/assets/3459374/26c75595-8984-4a9f-893a-e4b6d838b7f2)

## Розробка

Бажаєте зробити внесок у проект?

По-перше, дякую! Перегляньте [керівництво по внеску](./contributing.md) для отримання додаткової інформації.

## Ліцензія

MIT © [Денис Довгань][denysdovhan]

<!-- Badges -->

[gh-release-url]: https://github.com/denysdovhan/ha-yasno-outages/releases/latest
[gh-release-image]: https://img.shields.io/github/v/release/denysdovhan/ha-yasno-outages?style=flat-square
[gh-downloads-url]: https://github.com/denysdovhan/ha-yasno-outages/releases
[gh-downloads-image]: https://img.shields.io/github/downloads/denysdovhan/ha-yasno-outages/total?style=flat-square
[hacs-url]: https://github.com/hacs/integration
[hacs-image]: https://img.shields.io/badge/hacs-default-orange.svg?style=flat-square
[gh-sponsors-url]: https://github.com/sponsors/denysdovhan
[gh-sponsors-image]: https://img.shields.io/github/sponsors/denysdovhan?style=flat-square
[patreon-url]: https://patreon.com/denysdovhan
[patreon-image]: https://img.shields.io/badge/support-patreon-F96854.svg?style=flat-square
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
