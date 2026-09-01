<div align="center">

<img src="https://qgis.org/img/logosign.svg" alt="QGIS logo" width="120">

# QGIS Custom Splash Screen Manager

**A QGIS Processing script for installing, replacing, and safely reverting custom startup splash screens.**

[![QGIS](https://img.shields.io/badge/QGIS-3.40%2B-589632?style=for-the-badge&logo=qgis&logoColor=white)](https://qgis.org/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Processing](https://img.shields.io/badge/QGIS-Processing_Script-93B023?style=for-the-badge&logo=qgis&logoColor=white)](https://docs.qgis.org/latest/en/docs/user_manual/processing/console.html#creating-scripts-and-running-them-from-the-toolbox)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

![Windows](https://img.shields.io/badge/Windows-supported-0078D4?logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-supported-FCC624?logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/macOS-supported-000000?logo=apple&logoColor=white)
![Image size](https://img.shields.io/badge/output-600%C3%97300_PNG-blue)

</div>

---

## Overview

QGIS is highly customizable, including its startup splash screen. Normally, changing the splash requires manually enabling Interface Customization, locating the active user profile, editing `QGISCUSTOMIZATION3.ini`, preparing a correctly sized PNG, and entering the correct directory path.

This Processing script automates the entire workflow and provides a safe **Revert** action.

## Features

- Select a splash image from anywhere on your computer.
- Automatically creates the required `600 × 300` PNG.
- Supports PNG, JPG, JPEG, BMP, TIFF, and WebP images supported by Qt.
- Enables QGIS Interface Customization automatically.
- Uses the currently active QGIS user profile.
- Preserves unrelated toolbar, panel, menu, and interface customizations.
- Saves the original splash-related settings before the first installation.
- Allows the splash image to be replaced without overwriting the original backup.
- Restores the previous splash path and Interface Customization setting.
- Handles Windows paths automatically—no manual double-backslash editing.
- Includes compatibility handling for QGIS 3.40.1 and Qt 5.15.

## Requirements

| Component | Requirement |
|---|---|
| QGIS | QGIS 3.x, with QGIS 3.40+ recommended |
| Python | Included with QGIS; no extra packages required |
| Image | Any readable image; the script creates the required PNG |
| Restart | Required after installing, replacing, or reverting |

The script was designed around the following environment:

```text
QGIS 3.40.1-Bratislava
Qt 5.15.13
Python 3.12.7
```

## Installation

1. Download [`qgis_custom_splash_manager.py`](qgis_custom_splash_manager.py).
2. Open QGIS.
3. Open **Processing → Toolbox**.
4. Find **Scripts** in the Processing Toolbox.
5. Click the Scripts button and choose **Add Script to Toolbox…**
6. Select `qgis_custom_splash_manager.py`.
7. The tool will appear under:

```text
QGIS Customization
└── Custom Splash Screen Manager
```

You can also place the script directly in the active profile's `processing/scripts` directory and reload the Processing Scripts provider.

## Set or replace the splash screen

1. Open **Custom Splash Screen Manager** from the Processing Toolbox.
2. Set **Action** to **Set / replace custom splash screen**.
3. Browse to your preferred image.
4. Select a resize mode. **Crop to fill** is recommended.
5. Click **Run**.
6. Close and restart QGIS.

The script automatically:

1. Records the previous splash-related settings.
2. Converts the selected image to `600 × 300`.
3. Saves it as `splash.png` inside the active profile.
4. Updates `QGISCUSTOMIZATION3.ini`.
5. Enables Interface Customization.

## Resize modes

| Mode | Result |
|---|---|
| **Crop to fill (recommended)** | Preserves the aspect ratio, fills the entire splash, and crops excess edges |
| **Fit whole image with white padding** | Shows the complete image and adds white space where necessary |
| **Stretch to fill** | Forces the image to 600 × 300 and may distort it |
| **Require exactly 600 × 300** | Rejects images that are not already the correct dimensions |

## Revert to the original splash

1. Open **Custom Splash Screen Manager**.
2. Set **Action** to **Revert to previous QGIS splash screen**.
3. Leave **Splash image** empty.
4. Click **Run**.
5. Close and restart QGIS.

If a backup from the first installation exists, the script restores:

- The previous `splashpath` value, if one existed.
- The previous Interface Customization enabled/disabled state.
- The default QGIS splash when no earlier custom splash existed.

If the backup is missing, the script removes only the custom splash path. It deliberately leaves Interface Customization unchanged to protect any other GUI customizations.

## Files created in the active profile

On Windows, the default profile normally resembles:

```text
C:\Users\YourName\AppData\Roaming\QGIS\QGIS3\profiles\default\
```

The script manages these paths:

```text
QGIS/
├── QGISCUSTOMIZATION3.ini
├── QGISCUSTOMIZATION3.ini.before-custom-splash.bak
└── custom_splash/
    ├── splash.png
    └── previous_state.json
```

The full INI backup is an additional safety copy. Normal reversion uses the key-level `previous_state.json` backup so interface customizations made after splash installation are not overwritten.

## Important notes

> [!IMPORTANT]
> Restart QGIS after every install, replacement, or revert operation. QGIS reads the splash configuration during startup.

> [!NOTE]
> QGIS customizations are profile-specific. Run the script separately from each user profile that should use the custom splash.

> [!WARNING]
> Do not manually delete `previous_state.json` if you want the tool to restore the settings that existed before the first installation.

## Troubleshooting

### The default splash still appears

- Confirm that the algorithm finished without an error.
- Restart QGIS completely.
- Confirm you are using the same QGIS profile in which the script was run.
- Run the **Set / replace** action again.

### `QgsSettings` has no attribute `status`

Download the latest version of the script from this repository. This compatibility issue is fixed for QGIS 3.40.1.

### The image looks cropped

Use **Fit whole image with white padding** instead of **Crop to fill**, or prepare the source image at a 2:1 aspect ratio.

### I changed the image but QGIS still shows the previous one

Run the replacement again, confirm the algorithm finishes successfully, and then completely restart QGIS.

## How it works

The script uses `QgsApplication.qgisSettingsDirPath()` to locate the active profile. It writes the splash directory to the `Customization/splashpath` entry in `QGISCUSTOMIZATION3.ini` and enables `UI/Customization/enabled` through `QgsSettings`.

The selected image is loaded using Qt, auto-oriented when supported, resized, written to a temporary PNG, and atomically moved into place as `splash.png`.

## Contributing

Issues, suggestions, and pull requests are welcome. When reporting a problem, include:

- QGIS version
- Qt version
- Python version
- Operating system
- Complete Processing algorithm log

## License

Released under the [MIT License](LICENSE).

## Author

Created by [Hemed Lungo](https://github.com/Heed725).

---

<div align="center">

**Customize QGIS. Make it yours.**

[![Made with QGIS](https://img.shields.io/badge/Made_with-QGIS-589632?style=for-the-badge&logo=qgis&logoColor=white)](https://qgis.org/)

</div>
