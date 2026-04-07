# Rescue OIS Tablet App

Android tablet client for Rescue OIS. Talks only to the local vehicle K430 over HTTPS (mTLS). All map data is rendered offline from PMTiles served by the local edge.

## Build

```bash
./gradlew assembleDebug
```

## Test

```bash
./gradlew test
```

## Architecture

- **UI:** Jetpack Compose (`ui/MapScreen`, `ui/SiteDetailScreen`, `ui/IncidentScreen`, `ui/SyncStatusBar`)
- **Map:** MapLibre Native Android, offline tiles from local cache (`map/MapLibreWrapper`, `map/OfflineTileProvider`)
- **Local data:** Room (`data/local/AppDatabase`)
- **Remote:** Retrofit + OkHttp client to ops-api on the local K430 (`data/remote/EdgeApiClient`, `data/remote/SyncManager`)

## Network policy

- No internet
- No mesh access
- Outbound HTTPS only to the configured K430 endpoint, with the K430's pinned cert
- Knox Manage enforces the above at the device level
