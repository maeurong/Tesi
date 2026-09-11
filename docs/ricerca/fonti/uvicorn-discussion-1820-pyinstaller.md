Each time I run the compiled exe, there is a roughly 50% chance I get that error. I don't believe its a port conflict as the fastAPI server functions correctly and in task manager I can usually see 2-3 (should be 4) of the child proccesses(workers) spawn successfully. The error only occurs when num\_workers > 1 and no more than 2 workers ever seem to fail to start. When I don't get the error, all 4 workers spawn and function correctly. I cannot reproduce the issue while running wrapper2.py on its own

Python 3.10.2 and pyinstaller 5.1 and uvicorn version 0.20.0

Wrapper2.py

```
import uvicorn
from multiprocessing import Process, freeze_support
import socket
from ssdpy import SSDPServer

freeze_support()

def spawn_SSDP_Server_Thread(location, hostName):
    ...

    p = Process(target=server.serve_forever)
    p.start()

if __name__ == "__main__":
    freeze_support()
     
    #get free port
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]

    sock.close()

    hostName = socket.gethostname()
    ipAddress = socket.gethostbyname(hostName)

    num_workers = 4

    location = (ipAddress, port)

    spawn_SSDP_Server_Thread(location, hostName)

    uvicorn.run(
        "rest:app",
        host=str(ipAddress),
        port=int(port),
        reload=False,
        workers=int(num_workers),
    )
```

rest.py

```
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

pyinstaller command:

```
pyinstaller --onefile --hidden-import=rest --clean wrapper2.py
```

error:

```
←[32mINFO←[0m:     Uvicorn running on ←[1mhttp://192.168.0.23:60433←[0m (Press CTRL+C to quit)
←[32mINFO←[0m:     Started parent process [←[36m←[1m10560←[0m]
←[32mINFO←[0m:     Started server process [←[36m11536←[0m]
←[32mINFO←[0m:     Waiting for application startup.
←[32mINFO←[0m:     Application startup complete.
←[32mINFO←[0m:     Started server process [←[36m17836←[0m]
←[32mINFO←[0m:     Waiting for application startup.
←[32mINFO←[0m:     Application startup complete.
←[31mERROR←[0m:    Traceback (most recent call last):
  File "asyncio\runners.py", line 44, in run
  File "asyncio\base_events.py", line 641, in run_until_complete
  File "uvicorn\server.py", line 77, in serve
  File "uvicorn\server.py", line 119, in startup
  File "asyncio\base_events.py", line 1514, in create_server
  File "asyncio\base_events.py", line 313, in _start_serving
OSError: [WinError 10022] An invalid argument was supplied

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "starlette\routing.py", line 674, in lifespan
  File "uvicorn\lifespan\on.py", line 137, in receive
  File "asyncio\queues.py", line 159, in get
asyncio.exceptions.CancelledError

Process SpawnProcess-2:
Traceback (most recent call last):
  File "multiprocessing\process.py", line 315, in _bootstrap
  File "multiprocessing\process.py", line 108, in run
  File "uvicorn\_subprocess.py", line 76, in subprocess_started
  File "uvicorn\server.py", line 60, in run
  File "asyncio\runners.py", line 44, in run
  File "asyncio\base_events.py", line 641, in run_until_complete
  File "uvicorn\server.py", line 77, in serve
  File "uvicorn\server.py", line 119, in startup
  File "asyncio\base_events.py", line 1514, in create_server
  File "asyncio\base_events.py", line 313, in _start_serving
OSError: [WinError 10022] An invalid argument was supplied
←[32mINFO←[0m:     Started server process [←[36m3016←[0m]
←[32mINFO←[0m:     Waiting for application startup.
←[32mINFO←[0m:     Application startup complete.
←[32mINFO←[0m:     Started server process [←[36m22096←[0m]
←[32mINFO←[0m:     Waiting for application startup.
←[32mINFO←[0m:     Application startup complete.
```