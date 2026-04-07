# Tablet Enrollment

Field tablets are enrolled into Knox Manage and provisioned with the Rescue OIS app and an mTLS client certificate.

## Steps

1. **Knox Manage enrollment** — factory-reset tablet, enroll into the organizational Knox Manage tenant. Apply the **Rescue OIS field profile** which:
   - Disables sideloading
   - Locks Wi-Fi to the OPS-TABLET VLAN SSID/cert profile
   - Disables cellular and Bluetooth
   - Allowlists only the Rescue OIS app
2. **Install app** — push the latest Rescue OIS APK from Knox Manage.
3. **Issue mTLS client cert** — request a client certificate from the organizational CA bound to the tablet device ID. Install via Knox Manage credential store.
4. **Pin K430 server cert** — provision the local K430 server certificate (or its issuing CA) into the app's pinned trust store.
5. **First-run sync** — connect to vehicle, complete initial baseline sync (`/api/bootstrap`).
6. **Audit** — record enrollment event in core `audit.events`.

## TODO

- [ ] Document Knox Manage profile XML
- [ ] Document recovery procedure for lost / damaged tablet
