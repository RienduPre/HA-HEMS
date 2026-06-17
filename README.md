# HA-HEMS

Een eigen Home Assistant integratie voor Home Energy Management (HEMS) — gebouwd als robuust alternatief voor losse SEM-templates.

## Waarom HA-HEMS?

In plaats van te vertrouwen op fragiele entity-naam matching (zoals veel community HEMS-oplossingen doen), gebruikt HA-HEMS **`device_class`-gebaseerde discovery** gecombineerd met platform-herkenning. Dit maakt de integratie robuust tegen hernoemde entities en werkt direct met de meeste gangbare Nederlandse en internationale energie-hardware.

## Features

- **Automatische discovery** van zonnepanelen, slimme meters, thuisbatterijen, EV-laders en dynamische tarieven
- **Multi-device**: meerdere omvormers, meters, batterijen en laadpalen tegelijk
- **Slimme scheduler**: kiest laad-/ontlaadgedrag op basis van actueel Tibber/Nordpool/ENTSO-E tarief
- **Handmatige override** per laadpaal via een `select` entity, naast de automatische modus
- **Instelbare drempelwaarden** via de Options flow (geen herinstallatie nodig)

## Ondersteunde hardware

| Type | Platforms |
|---|---|
| Zonnepanelen | Growatt (Grott), SolarEdge, Fronius, Huawei, SMA, GoodWe, Enphase, SolarLog |
| Slimme meter | DSMR, P1 Monitor, HomeWizard, YouLess, Tibber Pulse |
| Thuisbatterij | Sessy, Solax, Huawei, GoodWe, FoxESS, Pylontech, Powervault |
| EV-lader | Wallbox, Easee, EVCC, Zaptec, Alfen, OCPP, ChargeAmps |
| Dynamisch tarief | Tibber, Nordpool, ENTSO-E, EasyEnergy, EnergyZero, aWATTar |

## Installatie

### Via HACS (custom repository)
1. HACS → Integraties → ⋮ → Aangepaste repositories
2. Voeg toe: `https://github.com/RienduPre/HA-HEMS`
3. Installeer "HA-HEMS", herstart Home Assistant
4. Instellingen → Apparaten en services → Integratie toevoegen → HA-HEMS

### Handmatig
1. Kopieer `custom_components/ha_hems` naar `/config/custom_components/`
2. Herstart Home Assistant
3. Voeg de integratie toe via de UI

## Configuratie

Bij het toevoegen van de integratie kun je alle velden leeg laten — discovery doet de rest. Wil je een specifieke entity forceren (bijv. als je meerdere zonnepanelen-achtige sensoren hebt), vul die dan handmatig in.

Na installatie kun je via **Instellingen → Apparaten en services → HA-HEMS → Configureren** de drempelwaarden aanpassen:
- Zonne-overschot start/stop drempel (W)
- Goedkoop/duur tarief grens (€/kWh)

## Entities

Na setup verschijnen onder andere:
- `sensor.hems_solar_power_total`
- `sensor.hems_grid_power_total`
- `sensor.hems_battery_soc_avg`
- `sensor.hems_ev_power_total`
- `sensor.hems_current_electricity_tariff`
- `select.hems_ev_<naam>_mode` — per laadpaal: auto / uit / zon / zon-of-goedkoop / snel
- `select.hems_mode_all_chargers` — globale override voor alle laadpalen

## Status

Functioneel compleet end-to-end. Actief in ontwikkeling bij Casa du Pré.

## Licentie

MIT
