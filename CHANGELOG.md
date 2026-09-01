# Changelog

All notable changes to this project are documented here.

## 1.0.0 — 2026-09-02

### Added

- Install or replace a QGIS custom startup splash screen.
- Select source images from any accessible location.
- Automatic `600 × 300` PNG generation.
- Crop, fit, stretch, and exact-size processing modes.
- Automatic Interface Customization activation.
- Active-profile detection through the QGIS API.
- Preservation of existing GUI customization entries.
- First-install state backup and full INI safety backup.
- Safe restoration of the earlier splash and customization settings.
- Windows, Linux, and macOS path handling.
- Compatibility handling for QGIS 3.40.1, where `QgsSettings` does not expose `status()`.
