
rem python setup.py py2exe

rem python setup.py install
rem python setup.py bdist

rem need Lib\site-packages\chromadb as dynamically loaded sql scripts for database init
rem --onefile 

rd /S /Q dist\FaiNlp

pyinstaller --noconsole ^
	--icon=src\FaiNlp\data\ItsLogo.png --splash=src\FaiNlp\data\fai.png ^
	--hidden-import=distutils ^
	--hidden-import=onnxruntime ^
	--hidden-import=kivy.garden ^
	--hidden-import=kivymd.uix.toolbar ^
	--hidden-import=kivymd.uix.bottomnavigation ^
	--hidden-import=kivymd.uix.scrollview ^
	--hidden-import=kivymd.uix.slider ^
	--hidden-import=kivymd.icon_definitions ^
	--hidden-import=tiktoken_ext ^
	--hidden-import=tiktoken_ext.openai_public ^
	--hidden-import=chromadb.telemetry.posthog ^
	--hidden-import=chromadb.api.segment ^
	--hidden-import=chromadb.db.impl ^
	--hidden-import=chromadb.migrations ^
	--hidden-import=chromadb.db.impl.sqlite ^
	--hidden-import=chromadb.segment.impl ^
	--hidden-import=chromadb.segment.impl.manager ^
	--hidden-import=chromadb.segment.impl.manager.local ^
	--hidden-import=chromadb.segment.impl.metadata ^
	--hidden-import=chromadb.segment.impl.metadata.sqlite ^
	--add-data=demo\DemoData.txt;.\demo ^
	--add-data=demo\DemoData.txt.article;.\demo ^
	--add-data=demo\DemoData.txt.storage;.\demo ^
	--add-data=demo\DemoScript.txt;.\demo ^
	--add-data=src\FaiNlp\LICENSE;.\ ^
	--add-data=src\FaiNlp\README.md;.\ ^
	--add-data=src\FaiNlp\data;.\data ^
	--add-data=src\FaiCommon\langchain;.\langchain ^
	--add-data=src\FaiCommon\VoiceCog\runtime;.\vosk ^
	--add-data=src\FaiCommon\VoiceCog\models\vosk-model-small-en-us-0.15;.\VoiceCog\models\vosk-model-small-en-us-0.15 ^
	--add-data=src\FaiCommon\ImageCog\models\ViT-B-32.pt;.\ImageCog\models\ ^
	--add-data=src\FaiCommon\ImageCog\runtime\bpe_simple_vocab_16e6.txt.gz;.\clip\ ^
	--add-data=Lib\site-packages\chromadb\migrations\embeddings_queue;chromadb\migrations\embeddings_queue ^
	--add-data=Lib\site-packages\chromadb\migrations\metadb;chromadb\migrations\metadb ^
	--add-data=Lib\site-packages\chromadb\migrations\sysdb;chromadb\migrations\sysdb ^
	src\FaiNlp\FaiNlp.py

rem pyinstaller --onefile --hidden-import=distutils --hidden-import=kivy.garden .\FaiNlp\FaiNlp.py 

