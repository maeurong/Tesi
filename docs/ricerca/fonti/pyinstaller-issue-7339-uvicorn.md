Windows 11  
Python 3.11  
Pyinstaller 5.7.0

When I'm running my fastapi app by the python interpreter everything goes fine. But when creating .exe file with pyinstaller, I'm geeting this error and crashes the .exe file.

My comand :

`pyinstaller --noconfirm --onedir --windowed --icon "D:/classifier/neural.ico" --add-data "D:/classifier/model;model/"  --collect-all "spacy" --collect-all "thinc" --collect-submodules "spacy_legacy" --copy-metadata "spacy_legacy" --collect-submodules "uvicorn" --collect-submodules "sklearn" --hidden-import "blis" --hidden-import "preshed" --hidden-import "fr_core_news_sm" --hidden-import "en_core_web_sm" --hidden-import "uvicorn" --hidden-import "uvicorn.logging" --paths "D:/classifier" --collect-submodules "D:/classifier"   "D:/launcher.py"`

```
Traceback (most recent call last):
  File "logging\config.py", line 541, in configure
  File "logging\config.py", line 653, in configure_formatter
  File "logging\config.py", line 472, in configure_custom
  File "uvicorn\logging.py", line 47, in __init__
    self.use_colors = sys.stdout.isatty()
                      ^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'isatty'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "launcher.py", line 47, in <module>
  File "uvicorn\main.py", line 506, in run
    config = Config(
             ^^^^^^^
  File "uvicorn\config.py", line 299, in __init__
    self.configure_logging()
  File "uvicorn\config.py", line 407, in configure_logging
    logging.config.dictConfig(self.log_config)
  File "logging\config.py", line 812, in dictConfig
  File "logging\config.py", line 544, in configure
ValueError: Unable to configure formatter 'default'
```

Any insight ?