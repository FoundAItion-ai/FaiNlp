rem moving Python virtual environment folder / venv should be avoided, create a new one instead
rem.
rem python -m venv FaiNlp 
rem pip freeze > requirements.txt
rem pip install -r requirements.txt
rem. *****************************************
rem The 'pathlib' package is an obsolete backport of a standard library package and is incompatible with PyInstaller. 
rem pip uninstall pathlib
rem. *****************************************
rem set PYTHONPATH=C:\Info\Projects\Docs\FoundAItion\Source\FaiNlp\src


pip list --outdated

pip freeze > requirements.txt

rem pip install -r requirements.txt --upgrade
rem remove py2exe?

rem pip install langchain --upgrade

rem pip install https://github.com/kivymd/KivyMD/archive/master.zip