# HCB Studio Host (Native)

Native kernel host for HCB Studio, compiled as a Windows `.exe`.

## Build
```bat
cd F:\HCB_STUDIO\00_Core\runtime\hcb_studio_host
build_release.bat
```

Binary output:
- `F:\HCB_STUDIO\00_Core\dist\hcb_studio_host.exe`

## Quick tests
```bat
F:\HCB_STUDIO\00_Core\dist\hcb_studio_host.exe status
F:\HCB_STUDIO\00_Core\dist\hcb_studio_host.exe event emit --event-type native_boot --note "ok"
F:\HCB_STUDIO\00_Core\dist\hcb_studio_host.exe concept list
F:\HCB_STUDIO\00_Core\dist\hcb_studio_host.exe plan --goal "status e motor ia"
```

## Scope (v0)
- status checks
- event bus emit/tail
- concept registry add/list
- plan generation from goal

Next step: installer packaging (Inno Setup/WiX) and service mode.
