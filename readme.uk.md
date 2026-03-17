[![SWUbanner](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua/)

![HA Yasno Outages Logo](./icons/logo.png)

# ⚡️ HA Yasno Outages

[![GitHub Release][gh-release-image]][gh-release-url]
[![GitHub Downloads][gh-downloads-image]][gh-downloads-url]
[![hacs][hacs-image]][hacs-url]
[![GitHub Sponsors][gh-sponsors-image]][gh-sponsors-url]
[![Buy Me A Coffee][buymeacoffee-image]][buymeacoffee-url]
[![Twitter][twitter-image]][twitter-url]

> [!NOTE]
> Інтеграція для графіків відключень електроенергії від [Yasno][yasno].
>
> Цей проєкт не має жодного відношення до [Yasno][yasno]. Ця інтеграція розроблена ентузіастом. Інформація може відрізнятися від інформації на офіційному сайті.

Ця інтеграція для [Home Assistant][home-assistant] надає інформацію про графіки відключень електроенергії від [Yasno][yasno]: календар запланованих відключень, датчики часу для наступних запланованих відключень тощо.

## Спонсорство

Ваша щедрість допоможе мені підтримувати та розробляти більше таких проектів, як цей.

- 💖 [Спонсорувати на GitHub][gh-sponsors-url]
- ☕️ [Buy Me A Coffee][buymeacoffee-url]
- Bitcoin: `bc1q7lfx6de8jrqt8mcds974l6nrsguhd6u30c6sg8`
- Ethereum: `0x6aF39C917359897ae6969Ad682C14110afe1a0a1`

## Встановлення

Найшвидший спосіб встановити цю інтеграцію — через [HACS][hacs-url], натиснувши кнопку нижче:

[![Add to HACS via My Home Assistant][hacs-install-image]][hasc-install-url]

Якщо це не працює, додайте цей репозиторій в HACS вручну, додавши цей URL:

1. Відвідайте **HACS** → **Інтеграції** → **...** (вгорі праворуч) → **Користувацькі репозиторії**
2. Натисніть **Додати**
3. Вставте `https://github.com/denysdovhan/ha-yasno-outages` у поле **URL**
4. Виберіть **Інтеграція** як **Категорію**
5. **Yasno Outages** з'явиться у списку доступних інтеграцій. Встановіть її звичайним способом.

## Використання

Ця інтеграція налаштовується через інтерфейс користувача. На сторінці **Пристрої та сервіси** натисніть **Додати інтеграцію** і знайдіть **Yasno Відключення**. Пройдіть кроки налаштування інтеграції.

Приклад процесу налаштування за адресою:

<https://github.com/user-attachments/assets/887300f1-2abf-4a08-a476-e9200ae6f8e7>

Після налаштування ви побачите свої налаштовані записи та відповідні сутності:

![Devices page](/media/devices.png)

![Device page](/media/device.png)

Далі можна додати інтеграцію на панель керування та переглядати інформацію про наступні заплановані відключення.
Інтеграція також надає календарний вигляд запланованих відключень. Ви можете додати його до панелі керування за допомогою [Calendar card][calendar-card].

![Calendars view](/media/calendars.png)

Приклади:

- [Автоматизація](/examples/automation.yaml)
- [Панель керування](/examples/dashboard.yaml)

Приклад панелі керування з цією інтеграцією:

![Приклад панелі керування](https://github.com/denysdovhan/ha-yasno-outages/assets/3459374/26c75595-8984-4a9f-893a-e4b6d838b7f2)

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
[buymeacoffee-url]: https://buymeacoffee.com/denysdovhan
[buymeacoffee-image]: https://img.shields.io/badge/support-buymeacoffee-222222.svg?style=flat-square
[twitter-url]: https://x.com/denysdovhan
[twitter-image]: https://img.shields.io/badge/follow-%40denysdovhan-000000.svg?style=flat-square

<!-- References -->

[yasno]: https://yasno.com.ua/
[home-assistant]: https://www.home-assistant.io/
[denysdovhan]: https://github.com/denysdovhan
[hasc-install-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=denysdovhan&repository=ha-yasno-outages&category=integration
[hacs-install-image]: https://my.home-assistant.io/badges/hacs_repository.svg
[add-translation]: https://github.com/denysdovhan/ha-yasno-outages/blob/master/contributing.md#how-to-add-translation
[calendar-card]: https://www.home-assistant.io/dashboards/calendar/
