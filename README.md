this is a fork

# Qingping IoT Cloud integration for Home Assistant

Home Assistant integration for Wi-Fi enabled Qingping devices connected to Qingping IoT Cloud (as opposed to [official integration](https://www.home-assistant.io/integrations/qingping/) which uses Bluetooth only). This integration uses [qingping-iot-cloud](https://github.com/danielskowronski/qingping-iot-cloud) library.
## How to use this

### Install

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zhaobenny&repository=HomeAssistantQingpingIoTCloud&category=integration)


### Connect to cloud

1. Download `Qingping IoT` app from [qingpingiot.com](https://www.qingpingiot.com/) or `Qingping+` app from [qingping.co/plus](https://www.qingping.co/plus)
2. Follow typical process or registering account and pairing device as per in-app instructions
3. Go to [developer.qingping.co](https://developer.qingping.co/login) and log in with relevant account
4. Navigate to [*Access Management*](https://developer.qingping.co/personal/permissionApply); from there copy *App Key* and *App Secret* values
   1. You get one set of credentials per account
   2. Those can't be revoked
5. In Home Assistant, add configure this custom integration with key-secret pair
   1. If you have multiple accounts across one or two platforms, you can add those as subsequent hubs
   2. *App ID* is added to hub name to avoid confusion

---

## Qingping IoT vs Qingping+

Those two apps are not the same and use different accounts.

For core functions, they are identical:

- they offer publicly available mobile apps with local binding, as well as local and cloud access
- both their account sets are valid authentication method to [developer.qingping.co](https://developer.qingping.co/) and thus data from both of them is available though same APIs
- you can use both of apps to pair devices which are accessible from this HA integration
- each supported device can be bound to both `Qingping IoT` and `Qingping+` apps at the same time

There are some differences:

- `Qingping IoT` is advertised for "proffesional" applications and supports some devices not sold to regular consumers
  - those can be bough from places like AliExpress
  - some of those "IoT" devices work with LoRaWAN or NB-IoT instead of Wi-Fi
  - this platform offers web dashboard which shows live data and historical readings
  - all Wi-Fi devices (and some BT ones via BT gateway) advertised for `Qingping+` work here
- `Qingping+` is advertised for household users and is sold in normal shops
  - this app supports some Bluetooth-only devices that are not compatible with Bluetooth gateway (like alarm clock) - those are not working with `Qingping IoT`
  - none of "IoT" devices are compatible


## Acknowledgements

This is a forked repository, see original.

This integration is based on [Example Home Assistant Integration - Integration 101 Template](https://github.com/msp1974/HAIntegrationExamples) by [Mark Parker](https://github.com/msp1974), which was originally distrubuted under MIT license. See [LICENSE](./LICENSE) file for full statement.
