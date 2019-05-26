import esp
import machine
import network
import ntptime
import os
import ssd1306
import sys
import utime

from micropython import const

import bme280
from urllib.urequest import urlopen

import config


DISPLAY_WIDTH = const(128)
DISPLAY_HEIGHT = const(64)

MAX_LOG_SIZE = const(64 * 1024)
LOG_NAME_MAIN = 'error.log'
LOG_NAME_SECONDARY = 'error.log.0'


def log_error(stage: str, err: Exception) -> None:
    """Log error to stdout (UART) and log file."""
    try:
        msg = 'Error during {}: {}'.format(stage, err)
        print(msg)
        sys.print_exception(err)

        log_size = 0
        try:
            # Get size of main log file.
            log_size = os.stat(LOG_NAME_MAIN)[6]
        except OSError:
            pass

        # Rotate log if size reaches limit.
        if log_size > MAX_LOG_SIZE:
            os.rename(LOG_NAME_MAIN, LOG_NAME_SECONDARY)

        with open(LOG_NAME_MAIN, 'a') as f:
            f.write(msg)
            f.write('\n')
    except:
        # This function is intended to log errors and there is no
        # sense to raise another exception as nothing could handle it.
        pass


def connect() -> None:
    """Connect to WiFi AP."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        # Wait for connection.
        for _ in range(20):
            if wlan.isconnected():
                return
            utime.sleep(1)

        raise Exception('Could not connect to network')


def cycle() -> None:
    """Measurement cycle."""
    # Init I2C.
    i2c = machine.I2C(scl=machine.Pin(config.SCL_PIN),
                      sda=machine.Pin(config.SDA_PIN))

    # Init BME280 sensor connected to I2C.
    bme = bme280.BME280(address=config.BME280_I2C_ADDR, i2c=i2c)

    # Read measurements.
    t, p, h = bme.read_compensated_data()
    t, p, h = t / 100, p / 256, h / 1024

    print(t, p, h)

    error = False
    # Sync RTC.
    try:
        ntptime.settime()
    except Exception as err:
        error = True
        log_error('syncing clock', err)

    url = config.URL_TEMPLATE.format(t=t, p=p, h=h)
    try:
        urlopen(url)
    except Exception as err:
        error = True
        log_error('sending metrics', err)

    # Init display.
    display = ssd1306.SSD1306_I2C(DISPLAY_WIDTH, DISPLAY_HEIGHT, i2c,
                                  addr=config.DISPLAY_I2C_ADDR)

    display.fill(0)

    # Calculate current time.
    hours = utime.localtime()[3] + config.UTC_OFFSET
    if hours >= 24:
        hours -= 24
    minutes = utime.localtime()[4]
    display.text('{:02d}:{:02d}'.format(hours, minutes),
                 DISPLAY_WIDTH - 40, 2)

    if error:
        display.text('Error', 0, 0)

    # Show measurements.
    display.text('T: {:.2f}C'.format(t), 0, 16)
    display.text('P: {:.2f}hPa'.format(p / 100), 0, 26)
    display.text('H: {:.2f}%'.format(h), 0, 36)

    display.show()
    utime.sleep(5)
    display.poweroff()


def main() -> None:
    """Main function."""
    try:
        connect()

        cycle()
    except Exception as err:
        log_error('main cycle', err)

    esp.deepsleep(config.CYCLE_TIME * 1_000_000)
    # Deep sleep doesn't start immediately. Pause to prevent
    # REPL to start.
    utime.sleep(2)


main()
