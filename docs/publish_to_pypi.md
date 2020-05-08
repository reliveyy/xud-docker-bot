# Publish to PyPI

Edit `~/.pypirc`.

```
[distutils]
index-servers = 
  pypi
  testpypi

[pypi]
username: alice
password: alicePassword

[testpypi]
username: alice
password: alicePassword
```

Create source and binary distributions. Please use the new wheel binary format. See also, [wheel vs egg](https://packaging.python.org/discussions/wheel-vs-egg/).

```
rm dist/*
python setup.sh sdist bdist_wheel
```

Upload to testpypi first

```
python -m twine upload --repository testpypi dist/*
```

Run newly uploaded package on another server.

```
sudo -H pip3 install --extra-index-url https://test.pypi.org/simple xud-docker-bot --upgrade
python3.8 -m bot --port 5000
```
