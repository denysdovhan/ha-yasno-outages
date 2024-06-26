# Contributing

If you plan to contribute back to this repo, please fork & open a PR.

## How to add translation

Only native speaker can translate to specific language.

1. Copy `custom_components/yasno_outages/translations/en.json` file and name it with appropriate language code.
1. Translate only keys in this file, not values.
1. Mention your translation in `readme.md` file.
1. Open a PR.
1. Find someone to check and approve your PR.

## How to run locally

1. Clone this repo to wherever you want:
   ```sh
   git clone https://github.com/denysdovhan/ha-yasno-outages.git
   ```
2. Go into the repo folder:
   ```sh
   cd ha-yasno-outages
   ```
3. Open the project with [VSCode Dev Container](https://code.visualstudio.com/docs/devcontainers/containers)
4. Start a HA via `Run Home Assistant on port 8123` task or run a following command:
   ```sh
   scripts/develop
   ```

Now you you have a working Home Assistant instance with this integration installed. You can test your changes by editing the files in `custom_components/yasno_outages` folder and restarting your Home Assistant instance.
