# Just Add Power - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A custom [Home Assistant](https://www.home-assistant.io/) integration for [Just Add Power](https://www.justaddpower.com/) MaxColor AV-over-IP systems. Exposes each decoder as a `media_player` entity with source selection, enabling control from the HA UI, automations, scripts, voice assistants, and remotes like the [Unfolded Circle Remote 3](https://www.unfoldedcircle.com/).

![Just Add Power](https://www.justaddpower.com/wp-content/uploads/2023/02/jp-mc-tx1-spec.pdf)

## Features

- **Media player entities** for each decoder with source switching via dropdown
- **Config flow** — set up entirely from the HA UI (Settings → Integrations)
- **Real-time state polling** — reads the decoder's multicast subscription to show which source is active
- **Optimistic updates** — UI reflects changes instantly, then confirms via poll
- **`switch_all_decoders` service** — switch every decoder to the same source in one call
- **Options flow** — add encoders/decoders after initial setup
- **Extra attributes** — exposes multicast address, channel number, and switching mode

## Requirements

- Just Add Power MaxColor Series encoders and decoders
- Firmware MAX v4.5.0 or later
- Devices configured in **Multicast** switching mode (not VLAN mode)
- Network connectivity from Home Assistant to the JAP device VLAN (inter-VLAN routing)
- Devices configured via AMP Alternate Configuration

## Installation

### HACS (Recommended)

1. In HACS, go to **Integrations → ⋮ (three dots) → Custom repositories**
2. Add this repository URL and select **Integration** as the category
3. Click **Add**, then find "Just Add Power" in the HACS store and install
4. Restart Home Assistant
5. Go to **Settings → Integrations → Add Integration → Just Add Power**

### Manual

1. Download the latest release from this repository
2. Copy the `custom_components/just_add_power` folder into your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant
4. Go to **Settings → Integrations → Add Integration → Just Add Power**

## Configuration

The config flow walks you through adding devices:

### 1. Add Encoders (Sources)

Enter a friendly name and the **Input #** (channel number) assigned by AMP during system setup.

| Name | Channel |
|------|---------|
| Android TV 1 | 1 |
| Android TV 2 | 2 |

### 2. Add Decoders (Displays)

Enter a friendly name and the decoder's **IP address** on the JAP VLAN.

| Name | IP Address |
|------|------------|
| Living Room | 172.17.100.1 |
| Patio | 172.17.100.2 |

The integration validates connectivity to each decoder during setup.

## Usage

### UI Control

Each decoder appears as a media player entity with a source dropdown. Selecting a source switches the decoder to that encoder's video stream.

### Automations & Scripts

```yaml
# Switch a single decoder
service: media_player.select_source
target:
  entity_id: media_player.living_room
data:
  source: "Android TV 1"
```

```yaml
# Switch all decoders at once
service: just_add_power.switch_all_decoders
data:
  source: "Android TV 2"
```

### Coordinated Audio/Video Switching

If you use a separate HDMI matrix for audio routing (e.g., using the TX2 HDMI loopout to an AVR), combine both switches in a single script:

```yaml
script:
  watch_android_tv_1_living_room:
    alias: "Watch Android TV 1 - Living Room"
    sequence:
      # Switch video (JAP decoder)
      - service: media_player.select_source
        target:
          entity_id: media_player.living_room
        data:
          source: "Android TV 1"
      # Switch audio (your HDMI matrix)
      - service: your_audio_matrix.switch
        data:
          input: 1
          output: 1
```

### Unfolded Circle Remote 3

The media player entities work natively with the UC Remote 3's Home Assistant integration. Create activities that combine video source switching with audio routing and TV power control.

## State Attributes

Each media player entity exposes these extra attributes:

| Attribute | Description | Example |
|-----------|-------------|---------|
| `multicast_address` | Current multicast group | `239.92.00.01` |
| `channel` | Current channel number | `1` |
| `device_ip` | Decoder IP address | `172.17.100.1` |
| `switching_mode` | Should be `multicast` | `multicast` |

## API Details

This integration communicates with JAP devices using the justOS HTTP API:

| Operation | Method | Endpoint | Body |
|-----------|--------|----------|------|
| Switch channel | POST | `/cgi-bin/api/command/channel` | Plain text channel number (e.g., `1`) |
| Get settings | GET | `/cgi-bin/api/settings` | — |

State is determined by reading `device.network.multicast` from the settings response. The multicast address `239.92.XX.YY` encodes the channel as `(XX × 256) + YY`.

## Network Setup

This integration is designed for JAP systems using **AMP Alternate Configuration** on a managed switch with:

- A dedicated VLAN for JAP devices (e.g., VLAN 101)
- IGMP snooping enabled with Fast Leave
- An IGMP Querier configured on the switch
- Jumbo Frames enabled
- Inter-VLAN routing so Home Assistant can reach the JAP VLAN

See the [JAP Ubiquiti setup guide](https://justaddpower.happyfox.com/kb/article/357-configuring-multicast-on-ubiquiti-switches/) for switch configuration details.

## Troubleshooting

**Integration can't connect to decoders during setup:**
- Verify the decoder IPs are correct
- Confirm Home Assistant can reach the JAP VLAN: `ping 172.17.100.1` from the HA host
- Check that no firewall rules block inter-VLAN traffic

**Source shows "Unknown":**
- The decoder is tuned to a channel not in your encoder list
- Update channel mappings via the integration's Options flow

**Switching returns OK but video doesn't change:**
- Verify all devices are in **Multicast** switching mode (check the web UI → Network page)
- If set to "VLAN", change to "Multicast" and hit Apply on all devices

**State doesn't update:**
- The integration polls every 10 seconds by default
- Check HA logs for API timeout errors, which could indicate network issues

## Contributing

Contributions are welcome! Please open an issue or PR.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not affiliated with or endorsed by Just Add Power. "Just Add Power" and "MaxColor" are trademarks of Just Add Power Cardware Co, Inc.
