# NexStar Control
This is a python 3.11+ library that can be used to communicate and control Celestron NexStar telescope devices.

## References
This package was created using the documentation found on the [NexStar Resrouce Site](https://www.nexstarsite.com/).

## Usage
For a more complete example of how to use this library, see the `sample.py` file in the root of this repository.

```python
from nexstar_control.device import NexStarHandControl

hc = NexStarHandControl("COM1")
if not hc.is_connected():
    print("Failed to connect to device")
    exit(1)

ra, dec = hc.get_position_ra_dec()
```