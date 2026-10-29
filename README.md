# dependency-pinner

**Turn a loose `requirements.txt` (`numpy`, `pandas>=2`) into exact versions from the
environment that actually produced your results, and check later whether an environment has drifted.**

Part of the *Research Automation Toolkit*: 100 open tools for daily research work.

## Why

Unpinned dependencies are a ticking reproducibility bomb: a new major version of NumPy, pandas or
scikit-learn changes defaults or removes functions, and the analysis that ran last year fails or,
worse, gives different numbers. `pip freeze` pins *everything* in the environment, including unrelated
packages. `dependency-pinner` pins exactly the packages you listed, preserving comments, extras and markers.

## Features

- Pins listed requirements to installed versions: `exact` (`==`), `compatible` (`~=X.Y`) or `minimum` (`>=`)
- Keeps comments, extras (`pkg[extra]`), environment markers, `-r`/`-e` lines and VCS URLs untouched
- Detects installed versions that violate the declared specifier and packages that are not installed
- `check`: drift report (ok / mismatch / missing / unpinned), exit 1 on problems (`--strict` for unpinned)
- PEP 503 name normalization and numeric version comparison (1.10 > 1.9)

## Usage

```bash
pip install .
dependency-pinner pin requirements.in -o requirements.txt
dependency-pinner pin requirements.txt -m compatible -o requirements.txt
dependency-pinner check requirements.txt --strict
```

## Testing

```bash
python -m unittest discover -s tests -t .
```

## License

MIT (c) JANIN A APURBA
