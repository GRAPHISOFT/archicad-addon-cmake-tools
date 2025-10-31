import json
import os
import requests
import zipfile
import subprocess
import sys
import tempfile
import platform
from pathlib import Path


def Main () -> None:
    projectRoot = Path (__file__).parent.parent
    with open (projectRoot / 'APIDevKitLinks.json', 'r') as f:
        apiDevKitLinks = json.load (f)

    with tempfile.TemporaryDirectory () as tempDirStr:
        tempDir = Path (tempDirStr)
        print (f'Using temporary directory: {tempDir}')

        if platform.system () == 'Windows':
            platformSign = 'WIN'
        elif platform.system () == 'Darwin':
            platformSign = 'MAC'
        else:
            raise RuntimeError ('Unsupported platform')

        for version, urlStr in apiDevKitLinks[platformSign].items ():
            url = Path (urlStr)

            print (f'Downloading: {url}')
            zipPath = tempDir / url.name
            with open (zipPath, 'wb') as f:
                f.write (requests.get (urlStr).content)

            print (f'Extracting: {zipPath}')
            extractDir = tempDir / url.stem
            extractDir.mkdir (exist_ok=True, parents=True)
            with zipfile.ZipFile (zipPath, 'r') as f:
                f.extractall (extractDir)

            testEnv = os.environ.copy ()
            testEnv['APIDEVKIT_DIR'] = str (extractDir)
            testEnv['APIDEVKIT_VERSION'] = version
            subprocess.run ([sys.executable, '-m', 'unittest', 'test_JsonToGrcConverter.test_JsonToGrcConverter'], env=testEnv, check=True, cwd=projectRoot)


if __name__ == "__main__":
    Main ()
