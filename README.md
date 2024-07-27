# NexStar Control
![Tests](https://github.com/tristeng/nexstar-control/actions/workflows/python-package.yml/badge.svg)

This is a python 3.11+ library that can be used to communicate and control Celestron NexStar telescope devices. The 
library does not have support for GPS units or CGE mounts (but could easily be added).

This library was created as an exercise to see if I could image the ISS with my telescope.

To see the latest features and updates, please see the [CHANGELOG](CHANGELOG.md). If you would like to request a feature
or report a bug, please submit directly on the issues tracker on [GitHub](https://github.com/tristeng/nexstar-control/issues).

## Installation
To install this package, you can use pip:
```shell
pip install nexstar-control
```

or with Poetry
```shell
poetry add nexstar-control
```

## Dependencies
This package has the following dependencies:
- [pyserial](https://pypi.org/project/pyserial/)
- [tzdata](https://pypi.org/project/tzdata/)

## API Reference
This package was created using the documentation found on the [NexStar Resrouce Site](https://www.nexstarsite.com/).

## Usage
For a more complete example of how to use this library, see the [`sample.py`](sample.py) file in the root of this 
repository.

```python
import datetime
from zoneinfo import ZoneInfo

from nexstar_control.device import NexStarHandControl, TrackingMode, LatitudeDMS, LongitudeDMS

hc = NexStarHandControl("COM1")
if not hc.is_connected():
    print("Failed to connect to device")
    exit(1)

# get the current position of the telescope in ra/dec or alt/az coordinates
ra, dec = hc.get_position_ra_dec()
alt, az = hc.get_position_alt_az()

# issue go to commands in ra/dec coordinates or alt/az coordinates
hc.goto_ra_dec(180, 0)
hc.goto_alt_az(90, 0)

# turn the telescope tracking mode off when doing slewing, but save the current mode to restore later
current_tracking_mode = hc.get_tracking_mode()
hc.set_tracking_mode(TrackingMode.OFF)

# slew the telescope at fixed rates (where negative values indicate the opposite direction)
hc.slew_fixed(9, -9)

# slew the telescope at variable rates (where negative values indicate the opposite direction)
hc.slew_variable(15000, -15000)

# restore the tracking mode
hc.set_tracking_mode(current_tracking_mode)

# set the location and time of the telescope
hc.set_location(lat=LatitudeDMS.from_decimal(49.2849), lng=LongitudeDMS.from_decimal(-122.8678))
dt = datetime.datetime.now(tz=ZoneInfo("America/Vancouver"))
hc.set_time(dt)
```

## Development
This package usings [Poetry](https://python-poetry.org/) for dependency management and packaging. To install the 
development dependencies, run the following command:
```shell
poetry install
```

### Formatting
This package uses [ruff](https://github.com/astral-sh/ruff) for code formatting and linting. To format the code, run the
following command:
```shell
poetry run ruff format
```

To lint the code, run the following command:
```shell
poetry run ruff check --fix
```

### Pre-commit
This package uses [pre-commit](https://pre-commit.com/) to run the formatting and linting checks before committing. To
install the pre-commit hooks, run the following command:
```shell
poetry run pre-commit install
```

### Testing
This package uses [pytest](https://docs.pytest.org/en/8.3.x/) for testing. To run the tests, run the following command:
```shell
poetry run pytest
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements
- [NexStar Resource Site](https://www.nexstarsite.com/)
  - website hosted by Michael Swanson
- [Celestron](https://www.celestron.com/)
