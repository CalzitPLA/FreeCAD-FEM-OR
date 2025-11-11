# FreeCAD OpenRadioss Workbench
# (c) 2023 Your Name
#
# This file initializes the OpenRadioss workbench

import os
import FreeCAD as App
import FreeCADGui as Gui

# Import the workbench class
from . import __title__, __author__, __url__, __license__

# Get the path to the resources
ICONPATH = os.path.join(os.path.dirname(__file__), "resources")
TRANSLATIONSPATH = os.path.join(ICONPATH, "translations")

# Set up translations
try:
    translate = App.Qt.translate
    QT_TRANSLATE_NOOP = App.Qt.QT_TRANSLATE_NOOP
except Exception as e:
    # Fallback if translation system is not available
    def translate(context, text):
        return text
    QT_TRANSLATE_NOOP = lambda context, text: text

# Add translations path
Gui.addLanguagePath(TRANSLATIONSPATH)
Gui.updateLocale()

# Print a message to the console
App.Console.PrintLog("Loading OpenRadioss workbench...\n")

# The workbench class is now defined in __init__.py
# This file is kept for backward compatibility and to ensure the workbench is loaded
