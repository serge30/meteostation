deps: bme280 urequest

lib:
	mkdir -p lib

bme280: lib
	wget -P lib https://raw.githubusercontent.com/serge30/mpy_bme280_esp8266/master/bme280.py

urequest: lib
	mkdir -p lib/urllib
	wget -P lib/urllib https://raw.githubusercontent.com/micropython/micropython-lib/master/urllib.urequest/urllib/urequest.py
