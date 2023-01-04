![Art Institute of Chicago](https://raw.githubusercontent.com/Art-Institute-of-Chicago/template/main/aic-logo.gif)

# Google Vision Tags
> A script to get AI-generated tags from Google image recognition API

This script takes an input csv containing artwork data and outputs a csv with labels from the Google Vision API.

As of January 2023, this code is experimental and currently in development.

## Requirements

* Python 3.6+
* macOS

Python 3.6+ requires the installation of an SSL certificate, to install in terminal run:

``` bash
/Applications/Python\ 3.11/Install\ Certificates.command
```

or to skip installation and use a deprecated ssl context set `--use-deprecated-ssl-context` to `true`.

## Usage

Use `--help` flag to see a full list of arguments and explanations:

```
python3 ./aic_google_vision_script.py --help
```

The only required arguments are `api-key` and `input-csv`. You can generate and manage Google Cloud API
keys in the [Google Cloud web console](https://console.cloud.google.com/apis/credentials).
Here is a full list of arguments with the values used to generate the output delivered with completion of this work:

```
python3 ./aic_google_vision_script.py \
    --api-key API_KEY \
    --input-csv input/All_Paintings_CSV_2022DEC23.csv \
    --output-csv output/All_Paintings_CSV_2022DEC23_output.csv \
    --failed-row-csv output/All_Paintings_CSV_2022DEC23_failed_rows.csv \
    --log-level info \
    --max-labels 50 \
    --batch-size 4 \
    --label-filters "Art,Visual Arts,Artist,Paint" \
    --use-deprecated-ssl-context false \
    --throttle-time 5
```
## Configuration

Following is a description of all of the configurations that can be entered when
using the script:

### `api-key`
Type: `String`

Required

A key provided by Google to authorize access to their API.

Example:
```bash
--api-key XXXX
```

### `input-csv`
Type: `String`

Required

Relative path to input CSV Keep all input files in the [/input](input) folder. CSV should
include the following columns:

* Title
* Artist Title
* Id
* Website URL
* IIIF Image URL

Example:
```bash
--input-csv input/artworks_20230101.csv
```

### `output-csv`
Type: `String`

Default: `output#` where `#` is an incremented number

Relative path to output CSV. Keep all output files in the [/output](output) folder.

Example:
```bash
--output-csv output/artworks_20230101_output.csv
```

### `failed-row-csv`
Type: `String`

Default: `failed_rows#` where `#` is an incremented number

All rows that failed from input csv are copied here for easier retry. Keep all output files in the [/output](output) folder.

Example:
```bash
--failed-row-csv output/artworks_20230101_failed_rows.csv
```

### `log-level`
Type: `String`

Default: `info`

Sets verbosity of execution logging. Allowed values are [`debug`, `info`, `warn`, `error`].

Example:
```bash
--log-level info
```

### `max-labels`
Type: `Integer`

Default: `50`

The maximum number of labels for each input image.

Example:
```bash
--max-labels 50
```

### `batch-size`
Type: `Integer`

Default: `6`

The number of images included in each request to Google vision API.

Example:
```bash
--batch-size 4
```

### `label-filters`
Type: `String`

Default:

Comma separated labels to filter out for all images. (eg art, painting, etc).

Example:
```bash
--label-filters "Art,Visual Arts,Artist,Paint"
```

### `use-deprecated-ssl-context`
Type: `Boolean`

Default: `false`

Use a deprecated ssl context.

Example:
```bash
--use-deprecated-ssl-context true
```

### `throttle-time`
Type: `Float`

Default: `2.5`

Amount of time in seconds to wait between processing each batch, needed to avoid usage limits on API.

Example:
```bash
--throttle-time 5
```

### `starting-row-number`
Type: `Integer`

Default: `1`

Row number of `input-csv` to begin processing on.

Example:
```bash
--starting-row-number 4
```

### `ending-row-number`
Type: `Integer`

Default: System's maximium integer size

Row number of `input-csv` to end processing on.

Example:
```bash
--ending-row-number 50
```

### `overwrite-output-files`
Type: `Boolean`

Default: `false`

Whether to overwrite output files, if false output will be appended to files if they exist.

Example:
```bash
--overwrite-output-files true
```

## Contributing

We encourage your contributions. Please fork this repository and make your changes in a separate branch. To better understand how we organize our code, please review our [version control guidelines](https://docs.google.com/document/d/1B-27HBUc6LDYHwvxp3ILUcPTo67VFIGwo5Hiq4J9Jjw).

```bash
# Clone the repo to your computer
git clone git@github.com:your-github-account/google-vision-tags.git

# Enter the folder that was created by the clone
cd google-vision-tags

# Start a feature branch
git checkout -b feature/good-short-description

# ... make some changes, commit your code

# Push your branch to GitHub
git push origin feature/good-short-description
```

Then on github.com, create a Pull Request to merge your changes into our
`main` branch.

This project is released with a Contributor Code of Conduct. By participating in
this project you agree to abide by its [terms](CODE_OF_CONDUCT.md).

We welcome bug reports and questions under GitHub's [Issues](issues). For other concerns, you can reach our engineering team at [engineering@artic.edu](mailto:engineering@artic.edu)


## Acknowledgements

Initial development by Elliot Korte.

## Licensing

This project is licensed under the [GNU Affero General Public License
Version 3](LICENSE).
