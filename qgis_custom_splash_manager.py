"""
QGIS Processing script: Custom Splash Screen Manager

Install this file in the Processing Toolbox scripts folder, then run either:
  - Set / replace custom splash screen
  - Revert to the previous QGIS splash screen

The script works on the active QGIS user profile only. QGIS must be restarted
before a splash-screen change becomes visible.
"""

import json
import os
import shutil

from qgis.PyQt.QtCore import QDir, QSettings, Qt
from qgis.PyQt.QtGui import QColor, QImage, QImageReader, QPainter
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputString,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsSettings,
)


class CustomSplashScreenManager(QgsProcessingAlgorithm):
    ACTION = "ACTION"
    SPLASH_IMAGE = "SPLASH_IMAGE"
    RESIZE_MODE = "RESIZE_MODE"

    STATUS = "STATUS"
    PROFILE_FOLDER = "PROFILE_FOLDER"
    CUSTOMIZATION_FILE = "CUSTOMIZATION_FILE"
    INSTALLED_SPLASH = "INSTALLED_SPLASH"

    ACTION_SET = 0
    ACTION_REVERT = 1

    MODE_CROP = 0
    MODE_FIT = 1
    MODE_STRETCH = 2
    MODE_EXACT = 3

    WIDTH = 600
    HEIGHT = 300
    ENABLED_KEY = "UI/Customization/enabled"
    SPLASH_KEY = "Customization/splashpath"
    STATE_SCHEMA = 1

    def createInstance(self):
        return CustomSplashScreenManager()

    def name(self):
        return "custom_splash_screen_manager"

    def displayName(self):
        return "Custom Splash Screen Manager"

    def group(self):
        return "QGIS Customization"

    def groupId(self):
        return "qgis_customization"

    def shortHelpString(self):
        return (
            "Sets or reverts the startup splash screen for the active QGIS user "
            "profile. Pick an image from anywhere; the script copies it into the "
            "profile and saves it as the required 600 x 300 splash.png.\n\n"
            "Set / replace: enables Interface Customization, preserves the existing "
            "customization file, records the previous splash-related settings, and "
            "installs the selected image.\n\n"
            "Revert: restores the splash path and Interface Customization setting "
            "that existed before the first run. If no manager backup exists, only "
            "the splash path is removed so other interface customizations remain safe.\n\n"
            "Restart QGIS after running the tool. Changes apply only to the active "
            "user profile."
        )

    def flags(self):
        # This algorithm changes settings used by the running QGIS application.
        legacy_flag = getattr(QgsProcessingAlgorithm, "FlagNoThreading", None)
        if legacy_flag is not None:
            return super().flags() | legacy_flag

        # QGIS 4 uses the scoped Qgis processing flag enum.
        flag_enum = getattr(Qgis, "ProcessingAlgorithmFlag", None)
        no_threading = getattr(flag_enum, "NoThreading", 0)
        return super().flags() | no_threading

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterEnum(
                self.ACTION,
                "Action",
                options=[
                    "Set / replace custom splash screen",
                    "Revert to previous QGIS splash screen",
                ],
                defaultValue=self.ACTION_SET,
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.SPLASH_IMAGE,
                "Splash image (not required when reverting)",
                behavior=self._file_behavior(),
                fileFilter=(
                    "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;"
                    "All files (*.*)"
                ),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.RESIZE_MODE,
                "Resize to 600 x 300",
                options=[
                    "Crop to fill (recommended)",
                    "Fit whole image with white padding",
                    "Stretch to fill",
                    "Require image to already be exactly 600 x 300",
                ],
                defaultValue=self.MODE_CROP,
            )
        )

        self.addOutput(QgsProcessingOutputString(self.STATUS, "Status"))
        self.addOutput(
            QgsProcessingOutputString(self.PROFILE_FOLDER, "Active profile folder")
        )
        self.addOutput(
            QgsProcessingOutputString(
                self.CUSTOMIZATION_FILE, "QGIS customization file"
            )
        )
        self.addOutput(
            QgsProcessingOutputString(self.INSTALLED_SPLASH, "Managed splash file")
        )

    def processAlgorithm(self, parameters, context, feedback):
        action = self.parameterAsEnum(parameters, self.ACTION, context)
        resize_mode = self.parameterAsEnum(parameters, self.RESIZE_MODE, context)
        source_image = self.parameterAsFile(parameters, self.SPLASH_IMAGE, context)

        profile_dir = os.path.normpath(QgsApplication.qgisSettingsDirPath())
        qgis_dir = os.path.join(profile_dir, "QGIS")
        ini_path = os.path.join(qgis_dir, self._customization_filename())
        managed_dir = os.path.join(qgis_dir, "custom_splash")
        splash_path = os.path.join(managed_dir, "splash.png")
        state_path = os.path.join(managed_dir, "previous_state.json")
        full_backup_path = ini_path + ".before-custom-splash.bak"

        if action == self.ACTION_SET:
            status = self._install(
                source_image,
                resize_mode,
                profile_dir,
                ini_path,
                managed_dir,
                splash_path,
                state_path,
                full_backup_path,
                feedback,
            )
        elif action == self.ACTION_REVERT:
            status = self._revert(
                ini_path,
                managed_dir,
                splash_path,
                state_path,
                feedback,
            )
        else:
            raise QgsProcessingException("Unknown action selected.")

        feedback.pushInfo("")
        feedback.pushInfo(status)
        feedback.pushInfo("Restart QGIS to see the change.")

        return {
            self.STATUS: status,
            self.PROFILE_FOLDER: profile_dir,
            self.CUSTOMIZATION_FILE: ini_path,
            self.INSTALLED_SPLASH: splash_path,
        }

    def _install(
        self,
        source_image,
        resize_mode,
        profile_dir,
        ini_path,
        managed_dir,
        splash_path,
        state_path,
        full_backup_path,
        feedback,
    ):
        if not source_image:
            raise QgsProcessingException(
                "Choose a splash image when using the Set / replace action."
            )
        source_image = os.path.abspath(source_image)
        if not os.path.isfile(source_image):
            raise QgsProcessingException(
                "The selected splash image does not exist: {}".format(source_image)
            )

        os.makedirs(managed_dir, exist_ok=True)

        ini_existed = os.path.isfile(ini_path)
        ini_settings = QSettings(ini_path, self._ini_format())
        app_settings = QgsSettings()

        # Preserve the state from the first install. Replacing the splash later
        # must not overwrite the values needed for a true revert.
        if not os.path.isfile(state_path):
            state = {
                "schema": self.STATE_SCHEMA,
                "profile_dir": profile_dir,
                "customization_file": ini_path,
                "ini_existed": ini_existed,
                "splash_key_existed": ini_settings.contains(self.SPLASH_KEY),
                "previous_splashpath": self._json_value(
                    ini_settings.value(self.SPLASH_KEY)
                ),
                "enabled_key_existed": app_settings.contains(self.ENABLED_KEY),
                "previous_enabled": self._json_value(
                    app_settings.value(self.ENABLED_KEY)
                ),
            }
            self._write_json_atomic(state_path, state)
            feedback.pushInfo("Saved the previous splash-related settings.")

            # Extra full-file safety backup. Revert uses the key-level state so
            # unrelated customizations made afterward are not overwritten.
            if ini_existed and not os.path.exists(full_backup_path):
                shutil.copy2(ini_path, full_backup_path)
                feedback.pushInfo(
                    "Created safety backup: {}".format(full_backup_path)
                )
        else:
            feedback.pushInfo(
                "Keeping the original backup from the first splash installation."
            )

        self._render_splash(source_image, splash_path, resize_mode)
        feedback.pushInfo("Created 600 x 300 PNG: {}".format(splash_path))

        # QGIS expects a directory here, including the final path separator.
        configured_dir = QDir.toNativeSeparators(os.path.join(managed_dir, ""))
        ini_settings.setValue(self.SPLASH_KEY, configured_dir)
        ini_settings.sync()
        self._raise_on_settings_error(
            ini_settings, "Could not update the QGIS customization file."
        )

        app_settings.setValue(self.ENABLED_KEY, True)
        app_settings.sync()
        self._raise_on_settings_error(
            app_settings, "Could not enable QGIS Interface Customization."
        )

        return (
            "Custom splash screen installed for the active profile. "
            "Interface Customization is enabled."
        )

    def _revert(self, ini_path, managed_dir, splash_path, state_path, feedback):
        os.makedirs(os.path.dirname(ini_path), exist_ok=True)
        ini_settings = QSettings(ini_path, self._ini_format())
        app_settings = QgsSettings()
        restored_from_backup = False
        previous_splashpath = None

        if os.path.isfile(state_path):
            state = self._read_state(state_path, ini_path)
            restored_from_backup = True

            if state.get("splash_key_existed", False):
                previous_splashpath = state.get("previous_splashpath")
                ini_settings.setValue(self.SPLASH_KEY, previous_splashpath)
            else:
                ini_settings.remove(self.SPLASH_KEY)

            if state.get("enabled_key_existed", False):
                app_settings.setValue(
                    self.ENABLED_KEY, state.get("previous_enabled")
                )
            else:
                app_settings.remove(self.ENABLED_KEY)

            feedback.pushInfo("Restored settings saved before the first install.")
        else:
            # Without a manager backup, removing only splashpath is safest.
            # Disabling customization here could hide a user's other intentional
            # interface changes.
            ini_settings.remove(self.SPLASH_KEY)
            feedback.pushWarning(
                "No manager backup was found. The custom splash path was removed, "
                "but Interface Customization was left unchanged to protect other "
                "GUI customizations."
            )

        ini_settings.sync()
        app_settings.sync()
        self._raise_on_settings_error(
            ini_settings, "Could not update the QGIS customization file."
        )
        self._raise_on_settings_error(
            app_settings, "Could not restore the Interface Customization setting."
        )

        # Remove only the file and state directory managed by this script. If
        # the previous configuration already pointed at the managed directory,
        # preserve the image because it is still the restored active splash.
        previous_dir = self._normalized_splash_dir(previous_splashpath)
        if previous_dir != os.path.normcase(os.path.normpath(managed_dir)):
            if os.path.isfile(splash_path):
                os.remove(splash_path)
            if restored_from_backup and os.path.isfile(state_path):
                os.remove(state_path)
            if os.path.isdir(managed_dir) and not os.listdir(managed_dir):
                os.rmdir(managed_dir)

        # If this script created a brand-new INI and it is empty again, remove
        # that empty file. Never remove a file containing other customizations.
        if restored_from_backup and not state.get("ini_existed", True):
            check_settings = QSettings(ini_path, self._ini_format())
            if not check_settings.allKeys() and os.path.isfile(ini_path):
                del check_settings
                os.remove(ini_path)

        if restored_from_backup:
            return "Previous QGIS splash-screen settings restored."
        return "Custom splash path removed; QGIS will use its default splash screen."

    def _render_splash(self, source_path, destination_path, resize_mode):
        reader = QImageReader(source_path)
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            detail = reader.errorString() or "unsupported or damaged image"
            raise QgsProcessingException(
                "QGIS could not read the selected image: {}".format(detail)
            )

        width = self.WIDTH
        height = self.HEIGHT
        smooth = self._qt_enum("SmoothTransformation", "TransformationMode")

        if resize_mode == self.MODE_EXACT:
            if image.width() != width or image.height() != height:
                raise QgsProcessingException(
                    "The image is {} x {} pixels. Exact mode requires 600 x 300."
                    .format(image.width(), image.height())
                )
            output = image
        elif resize_mode == self.MODE_STRETCH:
            ignore = self._qt_enum("IgnoreAspectRatio", "AspectRatioMode")
            output = image.scaled(width, height, ignore, smooth)
        elif resize_mode == self.MODE_FIT:
            keep = self._qt_enum("KeepAspectRatio", "AspectRatioMode")
            scaled = image.scaled(width, height, keep, smooth)
            output = QImage(width, height, self._image_argb32_format())
            output.fill(QColor("white"))
            painter = QPainter(output)
            painter.drawImage(
                (width - scaled.width()) // 2,
                (height - scaled.height()) // 2,
                scaled,
            )
            painter.end()
        else:
            expand = self._qt_enum(
                "KeepAspectRatioByExpanding", "AspectRatioMode"
            )
            scaled = image.scaled(width, height, expand, smooth)
            x = max(0, (scaled.width() - width) // 2)
            y = max(0, (scaled.height() - height) // 2)
            output = scaled.copy(x, y, width, height)

        temporary_path = destination_path + ".tmp.png"
        if os.path.isfile(temporary_path):
            os.remove(temporary_path)
        if not output.save(temporary_path, "PNG"):
            raise QgsProcessingException(
                "Could not save the processed splash image as PNG."
            )
        os.replace(temporary_path, destination_path)

    def _customization_filename(self):
        # QGIS 3 uses QGISCUSTOMIZATION3.ini. Keep the script ready for QGIS 4,
        # whose profile/customization generation is separate from QGIS 3.
        major = 3
        try:
            major = int(Qgis.QGIS_VERSION.split(".", 1)[0])
        except (AttributeError, TypeError, ValueError):
            pass
        return "QGISCUSTOMIZATION{}.ini".format(max(3, major))

    @staticmethod
    def _qt_enum(member_name, enum_name):
        # PyQt5 exposes Qt.KeepAspectRatio; PyQt6 exposes
        # Qt.AspectRatioMode.KeepAspectRatio. Support both forms.
        if hasattr(Qt, member_name):
            return getattr(Qt, member_name)
        return getattr(getattr(Qt, enum_name), member_name)

    @staticmethod
    def _file_behavior():
        if hasattr(QgsProcessingParameterFile, "File"):
            return QgsProcessingParameterFile.File
        return QgsProcessingParameterFile.Behavior.File

    @staticmethod
    def _ini_format():
        if hasattr(QSettings, "IniFormat"):
            return QSettings.IniFormat
        return QSettings.Format.IniFormat

    @staticmethod
    def _image_argb32_format():
        if hasattr(QImage, "Format_ARGB32"):
            return QImage.Format_ARGB32
        return QImage.Format.Format_ARGB32

    @staticmethod
    def _settings_no_error_value():
        if hasattr(QSettings, "NoError"):
            return QSettings.NoError
        return QSettings.Status.NoError

    def _raise_on_settings_error(self, settings, message):
        # QSettings exposes status(), but QgsSettings in QGIS 3.40 does not.
        # QgsSettings.sync() still commits the application setting, so only
        # perform the additional error check when the object supports it.
        status_method = getattr(settings, "status", None)
        if (
            callable(status_method)
            and status_method() != self._settings_no_error_value()
        ):
            raise QgsProcessingException(message)

    @staticmethod
    def _json_value(value):
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        return str(value)

    @staticmethod
    def _write_json_atomic(path, value):
        temporary_path = path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary_path, path)

    def _read_state(self, state_path, expected_ini_path):
        try:
            with open(state_path, "r", encoding="utf-8") as stream:
                state = json.load(stream)
        except (OSError, ValueError) as error:
            raise QgsProcessingException(
                "The splash manager backup is unreadable: {}".format(error)
            )

        if state.get("schema") != self.STATE_SCHEMA:
            raise QgsProcessingException(
                "The splash manager backup uses an unsupported format."
            )
        recorded_ini = os.path.normcase(
            os.path.normpath(str(state.get("customization_file", "")))
        )
        expected_ini = os.path.normcase(os.path.normpath(expected_ini_path))
        if recorded_ini != expected_ini:
            raise QgsProcessingException(
                "The saved backup belongs to a different QGIS profile."
            )
        return state

    @staticmethod
    def _normalized_splash_dir(value):
        if not value:
            return None
        return os.path.normcase(os.path.normpath(str(value)))
