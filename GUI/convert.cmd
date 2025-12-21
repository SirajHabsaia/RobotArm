pyside6-uic GUI\Designer\gui.ui > GUI\Designer\ui_gui.py
pyside6-rcc GUI\Designer\resources.qrc -o GUI\Designer\resources_rc.py
powershell -Command "(Get-Content GUI\Designer\ui_gui.py) -replace 'import resources_rc', 'import Designer.resources_rc' | Set-Content GUI\Designer\ui_gui.py"