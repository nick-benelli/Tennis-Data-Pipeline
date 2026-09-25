# Tennis-Data-Pipeline

Fetch, clean, and cross-link tennis match and tournament data from multiple
third-party sources into a consistent, versionable set of checkpoints for
analysis.

This repository is both an installable Python package (`tennis_data_pipeline`)
that implements the fetch/clean/link pipeline, and the collection of cleaned
datasets that pipeline produces (see [Data Sources](#data-sources) below).
**Note:** I am not the original creator of the data, only its custodian,
ensuring that any errors are corrected and the datasets are usable for
further analysis.

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/nick-benelli/Tennis-Data-Pipeline.git
cd Tennis-Data-Pipeline
uv sync --all-groups   # installs runtime + dev dependencies into .venv
```

To install just the package itself (e.g. as a dependency of another
project/environment):

```bash
uv pip install -e .
```

## Usage

Run the installed console script:

```bash
uv run tennis-data-pipeline
```

Day-to-day pipeline work (fetching, cleaning, building tournament tables,
linking matches across sources) happens via the per-source scripts under
[scripts/](scripts/) — see [docs/scripts/README.md](docs/scripts/README.md)
for the full CLI reference and example invocations. For how the pipeline
itself is organized (`datasources` → `handler` → `workflows` →
`loader`/`mapper`), see [docs/architecture/README.md](docs/architecture/README.md).

## Development

```bash
uv run pytest         # run the test suite
uv run ruff check .   # lint
uv run ruff format .  # format
uv run mypy           # type-check
```

[.pre-commit-config.yaml](.pre-commit-config.yaml) runs ruff check/format on
every commit; install the hooks once with `uv run pre-commit install`.

## Data Sources

The data in this repository comes from the following third-party sources:

- **[Tennis-Data.co.uk](http://www.tennis-data.co.uk/alldata.php)**: Provides historical data on tennis matches, including player results and odds.
- **[Jeff Sackmann's Tennis Abstract](https://www.tennisabstract.com/)**: Provides a comprehensive dataset on tennis players and matches. You can find the full repository on [Jeff Sackmann's GitHub](https://github.com/JeffSackmann).

Each dataset retains attribution to its original source, and the respective owners hold all rights. Please review each source's terms and conditions for more details on how their data can be used.

## Documentation

See [docs/](docs/README.md) for architecture, per-pipeline process docs, data-source references, and a CLI reference for every script.

## Disclaimer

- **Non-Commercial Use**: This repository is intended for personal, educational, or research purposes only. I do not profit from the distribution of this data.
- **Data Source Attribution**: All datasets in this repository come from third parties, with proper attribution given to the original creators. Any corrections or cleaning of the data have been made without altering its original intent.
- **No Warranty**: While efforts have been made to ensure accuracy, no warranties are made regarding the data. Always verify with the original source for the most up-to-date and complete data.

## Using the Data

Feel free to explore, analyze, and use the data for personal or educational purposes. Contributions are welcome via pull requests or issues.

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for more details.

### Creative Commons License

The tennis datasets hosted in this repository are licensed under a [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).  
This means you are free to use, share, and adapt the data for non-commercial purposes, as long as appropriate credit is given and any changes are shared under the same license.

**In other words**:
- **Attribution**: You must give appropriate credit to the source.
- **Non-commercial Use**: The data may only be used for non-commercial purposes.
- **ShareAlike**: If you modify the datasets, you must distribute your contributions under the same license.

For more details, see the full [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).


### Attribution

Per the license, proper credit is given to **Jeff Sackmann** and his work at **[Tennis Abstract](https://www.tennisabstract.com/)**.  
- **Appropriate Credit**: Attribution is required. 
- **Non-commercial Use**: This data may only be used for non-commercial purposes. 
- **ShareAlike**: If you make any changes or additions, you must distribute your contributions under the same license.
- **Changes**: This repository may include changes for data cleaning or structuring. These changes do not suggest that Jeff Sackmann or Tennis Abstract endorse this repository or its use.

For more details, see the full [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/#ref-same-license).
